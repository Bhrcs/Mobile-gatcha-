#include "Battle.h"
#include "Platform.h"
#include <cmath>

// ================================================================== Combatant
CombatantPtr Combatant::from_player_unit(const Json& unit, int slot)
{
    auto c = std::make_shared<Combatant>();
    const Json& d = DB.character(S(unit, "char_id"));
    c->def = d;
    c->id = S(d, "id");
    c->uid = S(unit, "uid");
    c->display_name = S(d, "name", "???");
    c->element = S(d, "element", "fire");
    c->level = I(unit, "level", 1);
    c->is_player = true;
    c->slot = slot;
    c->base_stats = Progression::unit_stats(d, c->level);
    c->max_hp = c->hp = I(c->base_stats["hp"]);
    c->normal_skill = S(d, "normal_attack");
    c->burst_skill = S(d, "burst");
    c->burst_level = std::clamp(I(unit, "burst_level", 1), 1, I(DB.balance("burst_levels", "max"), 5));
    c->burst_max = Progression::burst_cost(DB.skill(c->burst_skill), c->burst_level);
    for (auto& e : A(O(d, "passive"), "effects"))   // team-wide ("allies") passives are applied by BattleModel
        if (S(e, "scope", "self") != "allies") c->apply_aura(e);
    return c;
}

CombatantPtr Combatant::from_enemy(const std::string& enemy_id, int level, int slot, double hp_scale)
{
    auto c = std::make_shared<Combatant>();
    const Json& d = DB.enemy(enemy_id);
    c->def = d;
    c->id = enemy_id;
    c->display_name = S(d, "name", "???");
    c->element = S(d, "element", "fire");
    c->level = level;
    c->is_boss = B(d, "boss", false);
    c->slot = slot;
    c->base_stats = Progression::enemy_stats(d, level, hp_scale);
    c->max_hp = c->hp = I(c->base_stats["hp"]);
    c->normal_skill = S(O(d, "skills"), "normal");
    c->special_skill = S(O(d, "skills"), "special");
    c->skill_chance = F(O(d, "ai"), "skill_chance", 0.3);
    c->is_elite = B(d, "elite", false);
    const Json& br = O(d, "break");
    c->break_max = c->break_value = F(br, "max", 0);
    c->break_weak = S(br, "weak");
    for (auto& st : A(d, "start_statuses")) c->add_status(S(st, "id"), F(st, "value", 0), I(st, "turns", 99));
    return c;
}

void Combatant::apply_aura(const Json& e)
{
    double v = F(e, "value", 0);
    std::string k = S(e, "kind");
    if (k == "stat_up") passive_stats.push_back(e);
    else if (k == "heal_received_up") heal_received_up += v;
    else if (k == "damage_taken_down") damage_taken_down += v;
    else if (k == "burst_gain_up") burst_gain_mult += v;
    else if (k == "regen") regen_aura += v;
    else if (k == "crit_up") crit_bonus += v;
    else if (k == "guard_bonus") guard_bonus += v;
    else if (k == "damage_vs_low_hp") { bonus_vs_low_hp += v; low_hp_threshold = F(e, "threshold", 0.5); }
    else if (k == "damage_vs_debuffed") bonus_vs_debuffed += v;
}

void Combatant::apply_stat_bonus(const std::string& stat, double value)
{
    if (!base_stats.contains(stat)) return;
    base_stats[stat] = F(base_stats[stat]) * (1.0 + value);
    if (stat == "hp") max_hp = hp = (int)std::round(F(base_stats["hp"]));
}

Json Combatant::skill_data(const std::string& skill_id)
{
    if (is_player && skill_id == burst_skill && burst_level > 1)
    {
        if (!_skill_cache.contains(skill_id)) _skill_cache[skill_id] = Progression::scaled_burst(DB.skill(skill_id), burst_level);
        return _skill_cache[skill_id];
    }
    return DB.skill(skill_id);
}

double Combatant::get_stat(const std::string& stat) const
{
    double bonus = 0, cap = DB.balancef("combat", "status_stat_cap", 0.6);
    for (auto& s : statuses)
    {
        const Json& sd = DB.status(S(s, "id"));
        if (S(sd, "kind") == "stat_mod" && S(sd, "stat") == stat) bonus += F(s, "value", 0) * F(sd, "sign", 1);
    }
    bonus = std::clamp(bonus, -cap, cap);   // different buffs stack, but only up to the cap
    for (auto& p : passive_stats)
    {
        if (S(p, "stat") != stat) continue;
        if (S(p, "condition") == "hp_above" && hp_ratio() <= F(p, "threshold", 0)) continue;
        bonus += F(p, "value", 0);
    }
    if (stat == "atk") bonus += enrage;
    return F(at(base_stats, stat), 0) * std::max(1.0 + bonus, 0.1);
}

double Combatant::damage_bonus_vs(const Combatant& t) const
{
    double b = 0;
    if (bonus_vs_low_hp > 0 && t.hp_ratio() < low_hp_threshold) b += bonus_vs_low_hp;
    if (bonus_vs_debuffed > 0 && t.has_negative_status()) b += bonus_vs_debuffed;
    return b;
}

bool Combatant::has_negative_status() const
{
    for (auto& s : statuses)
        if (B(DB.status(S(s, "id")), "negative", false)) return true;
    return false;
}

// Chance a negative status fails to land: data "resist" per status (bosses default to boss_status_resist),
// + a diminishing-returns step for every time that status already landed on this boss.
double Combatant::status_resist(const std::string& id) const
{
    double base = is_boss ? DB.balancef("combat", "boss_status_resist", 0.3) : 0.0;
    double r = F(O(def, "resist"), id, base);
    if (is_boss) r += DB.balancef("combat", "boss_status_dr_step", 0.15) * I(status_hits, id, 0);
    return std::clamp(r, 0.0, 1.0);
}

// Removes up to `count` dispellable buffs (data: "dispellable": false protects boss mechanics).
std::vector<std::string> Combatant::dispel(int count)
{
    std::vector<std::string> removed;
    for (auto it = statuses.begin(); it != statuses.end() && (int)removed.size() < count;)
    {
        const Json& sd = DB.status(S(*it, "id"));
        if (!B(sd, "negative", false) && B(sd, "dispellable", true) && S(sd, "kind") != "charge")
        {
            removed.push_back(S(*it, "id"));
            it = statuses.erase(it);
        }
        else ++it;
    }
    if (!removed.empty()) statuses_changed.emit();
    return removed;
}

std::string Combatant::role() const
{
    std::string r = S(def, "role");
    for (auto& c : r) c = (char)std::tolower((unsigned char)c);
    return r;
}

int Combatant::shield_amount() const
{
    for (auto& s : statuses)
        if (S(s, "id") == "shield") return I(s, "value", 0);
    return 0;
}

void Combatant::remove_status(const std::string& id)
{
    size_t n = statuses.size();
    statuses.erase(std::remove_if(statuses.begin(), statuses.end(), [&](const Json& s) { return S(s, "id") == id; }),
                   statuses.end());
    if (statuses.size() != n) statuses_changed.emit();
}

double Combatant::damage_reduction() const
{
    double r = 0;
    for (auto& s : statuses)
        if (S(DB.status(S(s, "id")), "kind") == "damage_reduction") r = std::max(r, F(s, "value", 0));
    return std::clamp(r, 0.0, 0.9);
}

double Combatant::taunt_weight() const
{
    for (auto& s : statuses)
        if (S(DB.status(S(s, "id")), "kind") == "taunt") return DB.balancef("combat", "taunt_weight", 4.0);
    return 1.0;
}

// A Shield absorbs first (see last_absorbed). Returns the HP damage dealt.
int Combatant::take_damage(int amount)
{
    last_absorbed = 0;
    if (!is_alive()) return 0;
    for (auto it = statuses.begin(); it != statuses.end(); ++it)
        if (S(*it, "id") == "shield" && amount > 0)
        {
            int absorb = std::min(I(*it, "value", 0), amount);
            (*it)["value"] = I(*it, "value", 0) - absorb;
            amount -= absorb;
            last_absorbed = absorb;
            if (I(*it, "value", 0) <= 0) statuses.erase(it);
            statuses_changed.emit();
            break;
        }
    int dealt = std::clamp(amount, 0, hp);
    hp -= dealt;
    hp_changed.emit(hp, max_hp);
    if (hp <= 0)
    {
        hp = 0;
        burst = 0;
        statuses = Json::array();
        statuses_changed.emit();
        died.emit();
    }
    return dealt;
}

int Combatant::heal(int amount)
{
    if (!is_alive()) return 0;
    int healed = std::clamp(amount, 0, max_hp - hp);
    hp += healed;
    hp_changed.emit(hp, max_hp);
    return healed;
}

void Combatant::add_burst(double amount)
{
    if (!is_alive() || burst_skill.empty() || amount == 0) return;
    double before = burst;
    burst = std::clamp(burst + amount, 0.0, burst_max);
    if (burst != before) burst_changed.emit(burst, burst_max);
}

void Combatant::reset_burst()
{
    burst = 0;
    burst_changed.emit(burst, burst_max);
}

void Combatant::add_status(const std::string& id, double value, int turns)
{
    if (!is_alive() || DB.status(id).empty()) return;
    for (auto& s : statuses)
        if (S(s, "id") == id)
        {
            s["value"] = std::max(F(s, "value", 0), value);
            s["turns"] = std::max(I(s, "turns", 0), turns);
            statuses_changed.emit();
            return;
        }
    statuses.push_back({{"id", id}, {"value", value}, {"turns", turns}});
    statuses_changed.emit();
}

bool Combatant::has_status(const std::string& id) const
{
    for (auto& s : statuses)
        if (S(s, "id") == id) return true;
    return false;
}

std::vector<std::string> Combatant::cleanse(int count)
{
    std::vector<std::string> removed;
    for (auto it = statuses.begin(); it != statuses.end() && (int)removed.size() < count;)
        if (B(DB.status(S(*it, "id")), "negative", false))
        {
            removed.push_back(S(*it, "id"));
            it = statuses.erase(it);
        }
        else ++it;
    if (!removed.empty()) statuses_changed.emit();
    return removed;
}

Json Combatant::tick_statuses()
{
    Json events = Json::array();
    if (!is_alive()) return events;
    double regen = regen_aura;
    for (auto& s : statuses)
    {
        const Json& sd = DB.status(S(s, "id"));
        if (S(sd, "kind") == "dot")
            events.push_back({{"type", "dot"}, {"status", s["id"]},
                              {"amount", std::max(1, (int)std::round(max_hp * F(sd, "dot_percent_max_hp", 0.05)))}});
        else if (S(sd, "kind") == "hot")
            regen += F(s, "value", 0.05);
    }
    if (regen > 0 && hp < max_hp)
        events.push_back({{"type", "hot"}, {"status", "regen"},
                          {"amount", std::max(1, (int)std::round(max_hp * regen * (1.0 + heal_received_up)))}});
    for (auto it = statuses.begin(); it != statuses.end();)
    {
        if (S(*it, "id") == "charging") { ++it; continue; }   // released by the unit's next action
        (*it)["turns"] = I(*it, "turns", 0) - 1;
        if (I(*it, "turns", 0) <= 0) it = statuses.erase(it);
        else ++it;
    }
    statuses_changed.emit();
    return events;
}

// ================================================================== damage
namespace DamageCalculator
{
// raw = ATK x power; mitigated = raw - DEF x def_factor (>= raw x min ratio, >= 1);
// final = mitigated x element x crit x variance x (1 - reduction) x guard x bonus
Result calculate(const Combatant& a, const Combatant& t, const Json& skill, Rng& rng)
{
    const Json& cfg = O(DB.progression, "combat");
    double power = F(skill, "power", 1.0);
    int hits = std::max(1, I(skill, "hits", 1));
    double raw = a.get_stat("atk") * power;
    double mitigated = raw - t.get_stat("def") * F(cfg, "def_factor", 0.3);
    mitigated = std::max({mitigated, raw * F(cfg, "min_damage_ratio", 0.1), 1.0});
    double elem = DB.element_multiplier(a.element, t.element);
    bool crit = rng.randf() < F(cfg, "crit_chance", 0.05) + a.crit_bonus;
    double crit_mult = crit ? F(cfg, "crit_multiplier", 1.5) : 1.0;
    double variance = rng.randf_range(F(cfg, "variance_min", 0.95), F(cfg, "variance_max", 1.05));
    double guard = t.guarding ? 1.0 - std::min(F(cfg, "guard_reduction", 0.5) + t.guard_bonus, 0.8) : 1.0;
    // all mitigation (Bastion/armour statuses, passives, Guard) multiplies, then is capped: no immortal teams
    double taken = (1.0 - t.damage_reduction()) * (1.0 - std::clamp(t.damage_taken_down, 0.0, 0.5)) * guard;
    taken = std::max(taken, 1.0 - F(cfg, "max_mitigation", 0.8));
    double vuln = 0;   // Broken and other "damage_taken_up" statuses
    for (auto& s : t.statuses)
        if (S(DB.status(S(s, "id")), "kind") == "damage_taken_up") vuln = std::max(vuln, F(s, "value", 0));
    double bonus = (1.0 + a.damage_bonus_vs(t)) * (1.0 + vuln);
    int total = std::max(hits, (int)std::round(mitigated * elem * crit_mult * variance * taken * bonus));
    std::string tag = elem > 1.0 ? "WEAK" : (elem < 1.0 ? "RESIST" : "");
    return {total, split_hits(total, hits, A(skill, "hit_weights")), crit, elem, tag};
}

std::vector<int> split_hits(int total, int hits, const Json& weights)
{
    std::vector<double> w;
    double wsum = 0;
    for (int i = 0; i < hits; ++i)
    {
        w.push_back(i < (int)weights.size() ? F(weights[i], 1.0) : 1.0);
        wsum += w.back();
    }
    std::vector<int> out;
    int assigned = 0;
    for (int i = 0; i < hits; ++i)
    {
        int v = std::max((int)std::floor(total * w[i] / wsum), 1);
        out.push_back(v);
        assigned += v;
    }
    out[hits - 1] = std::max(1, out[hits - 1] + (total - assigned));   // rounding remainder on the final hit
    return out;
}

// Break damage per action: base x skill power x (Breaker role) x (break weakness element or element chart).
double break_amount(const Combatant& a, const Combatant& t, const Json& skill)
{
    if (t.break_max <= 0 || !a.is_player) return 0;
    const Json& cfg = O(DB.progression, "break");
    double v = F(cfg, "base", 12) * F(skill, "power", 1.0) * F(skill, "break_mult", 1.0);
    if (a.role() == "breaker") v *= F(cfg, "breaker_mult", 2.0);
    v *= (!t.break_weak.empty() && a.element == t.break_weak) ? F(cfg, "weak_mult", 1.5) : DB.element_multiplier(a.element, t.element);
    return v;
}

int heal_amount(const Combatant& c, const Combatant& t, const Json& e)
{
    double amount = t.max_hp * F(e, "percent_max_hp", 0) + c.get_stat("rec") * F(e, "rec_multiplier", 0);
    return std::max(1, (int)std::round(amount * (1.0 + t.heal_received_up)));
}
}  // namespace DamageCalculator

// ================================================================== BattleModel
void BattleModel::setup(const std::string& stage_id, const Json& party_units, int seed)
{
    stage = DB.stage(stage_id);
    waves = A(stage, "waves");
    if (seed >= 0) rng.seed((unsigned)seed);
    else rng.randomize();
    players.clear();
    for (size_t i = 0; i < party_units.size(); ++i) players.push_back(Combatant::from_player_unit(party_units[i], (int)i));
    apply_team_bonuses();
    wave_index = -1;
    advance_wave();
}

void BattleModel::apply_team_bonuses()
{
    for (auto& p : players)
        for (auto& e : A(O(p->def, "passive"), "effects"))
            if (S(e, "scope", "self") == "allies")
                for (auto& ally : players) ally->apply_aura(e);
    if (players.empty()) return;
    for (auto& e : A(O(players[0]->def, "leader_skill"), "effects"))
        for (auto& ally : players)
        {
            if (e.contains("element") && S(e, "element") != ally->element) continue;
            if (e.contains("stat")) ally->apply_stat_bonus(S(e, "stat"), F(e, "value", 0));
            else if (e.contains("kind")) ally->apply_aura(e);
        }
}

Units& BattleModel::advance_wave()
{
    ++wave_index;
    enemies.clear();
    if (wave_index > 0) wave_recovery();
    if (wave_index >= (int)waves.size()) return enemies;
    const Json& spawns = waves[wave_index];
    for (size_t i = 0; i < spawns.size(); ++i)
    {
        const Json& sp = spawns[i];
        std::string eid = S(sp, "enemy");
        if (sp.contains("enemy_by_leader_element")) eid = S(sp["enemy_by_leader_element"], leader_element(), eid);
        if (DB.enemy(eid).empty())
        {
            Platform::log("Stage " + S(stage, "id") + " references unknown enemy " + eid);
            continue;
        }
        enemies.push_back(Combatant::from_enemy(eid, I(sp, "level", 1), (int)i, F(sp, "hp_scale", 1.0)));
    }
    round_number = 0;
    refresh_auras();
    start_player_phase();
    wave_spawned.emit(wave_index);
    return enemies;
}

void BattleModel::wave_recovery()
{
    double pct = DB.balancef("combat", "wave_recovery_percent", 0.0);
    for (auto& p : alive(players))
    {
        auto& st = p->statuses;
        st.erase(std::remove_if(st.begin(), st.end(), [](const Json& s) { return B(DB.status(S(s, "id")), "negative", false); }),
                 st.end());
        p->statuses_changed.emit();
        if (pct > 0) p->heal((int)std::round(p->max_hp * pct));
    }
}

void BattleModel::start_player_phase()
{
    ++round_number;
    ++total_rounds;
    for (auto& p : players)
    {
        p->acted = !p->is_alive();
        p->guarding = false;
    }
}

bool BattleModel::players_can_act() const
{
    for (auto& p : players)
        if (p->can_act()) return true;
    return false;
}

CombatantPtr BattleModel::first_ready_player() const
{
    for (auto& p : players)
        if (p->can_act()) return p;
    return nullptr;
}

Units BattleModel::alive(const Units& list)
{
    Units out;
    for (auto& c : list)
        if (c->is_alive()) out.push_back(c);
    return out;
}

Units BattleModel::enemy_turn_order() const
{
    Units order = alive(enemies);
    std::stable_sort(order.begin(), order.end(), [](auto& a, auto& b) {
        double sa = a->get_stat("spd"), sb = b->get_stat("spd");
        return sa > sb || (sa == sb && a->slot < b->slot);
    });
    Units out;   // bosses with ai.actions > 1 act several times a round (their extra turns come last)
    for (auto& e : order) out.push_back(e);
    for (int k = 1; k < 4; ++k)
        for (auto& e : order)
            if (I(O(e->def, "ai"), "actions", 1) > k) out.push_back(e);
    return out;
}

std::vector<BattleEvent> BattleModel::end_round()
{
    std::vector<BattleEvent> events;
    Units all = alive(players);
    for (auto& e : alive(enemies)) all.push_back(e);
    for (auto& c : all)
    {
        for (auto& e : c->tick_statuses()) events.push_back({S(e, "type"), c, I(e, "amount", 0), S(e, "status")});
        if (c->break_max > 0 && c->break_value <= 0 && !c->is_broken())   // recovered: the gauge refills
        {
            c->break_value = c->break_max;
            c->break_changed.emit();
            events.push_back({"break_restore", c});
        }
    }
    return events;
}

int BattleModel::apply_dot(const CombatantPtr& u, int amount)
{
    int dealt = u->take_damage(amount);
    check_death(u);
    return dealt;
}

void BattleModel::guard(Combatant& u)
{
    u.guarding = true;
    u.acted = true;
    gain_burst(u, DB.balancef("burst", "gain_guard", 15));
}

Plan BattleModel::plan_action(const CombatantPtr& user, const std::string& skill_id, CombatantPtr target, bool use_burst)
{
    Plan plan;
    plan.skill_id = skill_id;
    plan.skill = user->skill_data(skill_id);
    plan.user = user;
    plan.is_burst = use_burst;
    if (use_burst)
    {
        user->reset_burst();
        if (user->is_player) bursts_used[user->uid] = I(bursts_used, user->uid, 0) + 1;
    }
    user->last_action = skill_id;
    Units& foes = foes_of(*user);
    std::string t = S(plan.skill, "target", "enemy_single");
    if (t == "enemy_single")
    {
        if (!target || !target->is_alive() || std::find(foes.begin(), foes.end(), target) == foes.end())
        {
            Units living = alive(foes);
            target = living.empty() ? nullptr : living[rng.randi_range(0, (int)living.size() - 1)];
        }
        if (target) plan.targets.push_back(plan_target(*user, target, plan.skill));
    }
    else if (t == "enemy_all")
    {
        for (auto& f : alive(foes)) plan.targets.push_back(plan_target(*user, f, plan.skill));
    }
    else if (t == "ally_lowest")
    {
        Units allies = alive(allies_of(*user));
        std::stable_sort(allies.begin(), allies.end(), [](auto& a, auto& b) { return a->hp_ratio() < b->hp_ratio(); });
        plan.ally_target = allies.empty() ? user : allies[0];
    }
    return plan;   // ally_all / self: resolved in finish_action
}

PlanTarget BattleModel::plan_target(const Combatant& user, const CombatantPtr& target, const Json& skill)
{
    auto d = DamageCalculator::calculate(user, *target, skill, rng);
    PlanTarget pt;
    pt.unit = target;
    pt.hits = d.hits;
    pt.crit = d.crit;
    pt.tag = d.tag;
    pt.total = d.total;
    pt.break_per_hit = DamageCalculator::break_amount(user, *target, skill) / std::max<size_t>(1, d.hits.size());
    return pt;
}

HitResult BattleModel::apply_hit(Plan& plan, int ti, int hi)
{
    PlanTarget& e = plan.targets[ti];
    if (!e.unit->is_alive() || hi >= (int)e.hits.size()) return {};
    HitResult r;
    r.skipped = false;
    r.dealt = e.unit->take_damage(e.hits[hi]);
    r.absorbed = e.unit->last_absorbed;
    e.dealt += r.dealt;
    e.absorbed += r.absorbed;
    e.landed = true;
    if (e.unit->is_player && (r.dealt > 0 || r.absorbed > 0) && !e.burst_given)
    {
        gain_burst(*e.unit, DB.balancef("burst", "gain_damaged", 6));
        e.burst_given = true;
    }
    Combatant& t = *e.unit;
    if (t.is_alive() && !t.charging_skill.empty())   // enough damage while it charges interrupts the attack
    {
        t.charge_damage += r.dealt + r.absorbed;
        double need = F(O(DB.skill(t.charging_skill), "interrupt"), "damage_percent", 0);
        if (need > 0 && t.charge_damage >= need * t.max_hp)
        {
            t.charging_skill.clear();
            t.remove_status("charging");
            r.interrupted = true;
        }
    }
    if (t.is_alive() && e.break_per_hit > 0 && t.break_value > 0 && !t.is_broken())
    {
        t.break_value = std::max(0.0, t.break_value - e.break_per_hit);
        t.break_changed.emit();
        if (t.break_value <= 0)
        {
            on_break(t);
            r.broke = true;
        }
    }
    r.killed = check_death(e.unit);
    return r;
}

// BROKEN: cancels a charged attack, strips break-removable armour, takes more damage and loses its next turn.
void BattleModel::on_break(Combatant& u)
{
    const Json& cfg = O(DB.progression, "break");
    u.charging_skill.clear();
    u.pending_charge.clear();
    u.remove_status("charging");
    for (auto it = u.statuses.begin(); it != u.statuses.end();)
        it = B(DB.status(S(*it, "id")), "removed_by_break", false) ? u.statuses.erase(it) : it + 1;
    u.add_status("broken", F(cfg, "damage_taken_up", 0.5), I(cfg, "turns", 2));
}

bool BattleModel::check_death(const CombatantPtr& u)
{
    if (u->is_alive()) return false;
    if (u->counted) return true;
    u->counted = true;
    if (u->is_player) ++players_ko;
    else on_enemy_killed(u);
    return true;
}

std::vector<BattleEvent> BattleModel::finish_action(Plan& plan)
{
    auto& user = plan.user;
    std::vector<BattleEvent> events;
    for (auto& effect : A(plan.skill, "effects"))
    {
        Units rec;
        std::string on = S(effect, "on", "target");
        if (on == "target")
        {
            for (auto& e : plan.targets)
                if (e.unit->is_alive() && e.landed) rec.push_back(e.unit);
        }
        else if (on == "allies") rec = alive(allies_of(*user));
        else if (on == "foes") rec = alive(foes_of(*user));
        else if (on == "target_ally") { if (plan.ally_target && plan.ally_target->is_alive()) rec = {plan.ally_target}; }
        else if (on == "self") { if (user->is_alive()) rec = {user}; }
        std::string type = S(effect, "type");
        for (auto& r : rec)
        {
            if (type == "heal")
                events.push_back({"heal", r, r->heal(DamageCalculator::heal_amount(*user, *r, effect))});
            else if (type == "cleanse")
                for (auto& sid : r->cleanse(I(effect, "count", 1))) events.push_back({"cleanse", r, 0, sid});
            else if (type == "status")
            {
                std::string sid = S(effect, "status");
                bool hostile = r->is_player != user->is_player && B(DB.status(sid), "negative", false);
                double chance = F(effect, "chance", 1.0), roll = rng.randf();
                if (roll < chance)
                {
                    if (hostile && roll >= chance * (1.0 - r->status_resist(sid)))
                        events.push_back({"resist", r, 0, sid});
                    else
                    {
                        r->add_status(sid, F(effect, "value", 0), I(effect, "duration", 1));
                        if (hostile && r->is_boss) r->status_hits[sid] = I(r->status_hits, sid, 0) + 1;
                        events.push_back({"status", r, 0, sid});
                    }
                }
            }
            else if (type == "dispel")
                for (auto& sid : r->dispel(I(effect, "count", 1))) events.push_back({"dispel", r, 0, sid});
            else if (type == "shield")
            {
                int amount = (int)std::round(user->max_hp * F(effect, "percent_caster_hp", 0.1));
                r->add_shield(amount, I(effect, "duration", 2));
                events.push_back({"shield", r, amount});
            }
            else if (type == "burst" && r != user)
            {
                r->add_burst(F(effect, "value", 0));
                events.push_back({"burst", r, I(effect, "value", 0)});
            }
        }
    }
    if (user->is_player && !plan.is_burst && user->is_alive()) gain_burst(*user, DB.balancef("burst", "gain_attack", 34));
    user->acted = true;
    return events;
}

std::vector<BattleEvent> BattleModel::resolve_instant(Plan& plan)
{
    for (size_t ti = 0; ti < plan.targets.size(); ++ti)
        for (size_t hi = 0; hi < plan.targets[ti].hits.size(); ++hi) apply_hit(plan, (int)ti, (int)hi);
    return finish_action(plan);
}

void BattleModel::begin_charge(Combatant& enemy, const std::string& skill_id)
{
    enemy.charging_skill = skill_id;
    enemy.charge_damage = 0;
    enemy.add_status("charging", 1.0, 9);
    enemy.acted = true;
}

// Boss phases (data: ai.phases = [{below, atk_up, pattern, announce, skill, charge, summon}], or the older
// single ai.phase2). Returns the phase entered (+ "index", "count"), one per call, or {}.
static Json phases_of(const Json& ai)
{
    if (ai.contains("phases")) return ai["phases"];
    return ai.contains("phase2") ? Json::array({ai["phase2"]}) : Json::array();
}

Json BattleModel::check_phase(Combatant& e)
{
    Json ph = phases_of(O(e.def, "ai"));
    if (!e.is_alive() || e.phase_index >= (int)ph.size() || e.hp_ratio() > F(ph[e.phase_index], "below", 0.5))
        return Json::object();
    Json p = ph[e.phase_index++];
    e.phase2 = true;
    e.enrage = std::max(e.enrage, F(p, "atk_up", 0));
    e.pattern_index = 0;
    if (p.contains("skill")) e.pending_skill = S(p, "skill");
    if (p.contains("charge")) e.pending_charge = S(p, "charge");
    p["index"] = e.phase_index;
    p["count"] = (int)ph.size();
    return p;
}

Units BattleModel::summon_minions(Combatant& boss, const Json& sm_in)
{
    const Json& sm = sm_in.is_object() ? sm_in : O(O(boss.def, "ai"), "summon");
    Units out;
    if (sm.empty() || DB.enemy(S(sm, "enemy")).empty()) return out;
    std::vector<int> used;
    for (auto& e : alive(enemies))
        if (e->summoned) used.push_back(e->summon_index);
    for (int i = 0; i < I(sm, "count", 1); ++i)
    {
        if (!can_summon(boss, sm)) break;
        int idx = 0;
        while (std::find(used.begin(), used.end(), idx) != used.end()) ++idx;
        used.push_back(idx);
        auto c = Combatant::from_enemy(S(sm, "enemy"), std::max(1, boss.level + I(sm, "level_offset", -2)), free_slot(), 1.0);
        c->summoned = true;
        c->summon_index = idx;
        c->acted = true;
        enemies.push_back(c);
        out.push_back(c);
    }
    boss.acted = true;
    refresh_auras();
    return out;
}

void BattleModel::refresh_auras()
{
    Json total = Json::object();
    for (auto& e : alive(enemies))
        if (e->def.contains("aura")) total[S(e->def["aura"], "status")] = F(total, S(e->def["aura"], "status"), 0) + F(e->def["aura"], "value", 0);
    for (auto& b : alive(enemies))
    {
        if (!b->is_boss) continue;
        for (auto& [sid, v] : total.items())
        {
            b->remove_status(sid);
            if (F(v) > 0) b->add_status(sid, F(v), 99);
        }
    }
}

bool BattleModel::can_summon(const Combatant& boss, const Json& sm_in) const
{
    const Json& sm = sm_in.is_object() ? sm_in : O(O(boss.def, "ai"), "summon");
    if (sm.empty()) return false;
    int minions = 0;
    Units al = alive(enemies);
    for (auto& e : al) minions += e->summoned ? 1 : 0;
    return minions < std::min(I(sm, "max", MAX_SUMMONED), MAX_SUMMONED) && (int)al.size() < MAX_ENEMIES_ALIVE;
}

int BattleModel::free_slot() const
{
    int s = 0;
    for (bool used = true; used; )
    {
        used = false;
        for (auto& e : enemies)
            if (e->slot == s) { used = true; ++s; break; }
    }
    return s;
}

void BattleModel::on_enemy_killed(const CombatantPtr& e)
{
    ++enemies_defeated;
    if (e->is_boss) ++bosses_defeated;
    if (e->def.contains("aura"))   // its aura fades with it
    {
        std::string sid = S(e->def["aura"], "status");
        for (auto& b : enemies) b->remove_status(sid);
        refresh_auras();
    }
    int xp = Progression::enemy_xp(e->def, e->level);
    Json loot = Progression::roll_enemy_loot(e->def, e->level, rng);
    if (e->summoned)   // minions: a little XP / Gold, no items (no farming a boss forever)
    {
        xp /= 2;
        loot["gold"] = I(loot["gold"]) / 2;
        loot["items"] = Json::object();
    }
    xp_earned += xp;
    gold_earned += I(loot["gold"]);
    for (auto& [id, q] : loot["items"].items()) items_earned[id] = I(items_earned, id, 0) + I(q);
    enemy_defeated.emit(e);
}

int BattleModel::total_bursts() const
{
    int n = 0;
    for (auto& [k, v] : bursts_used.items()) n += I(v);
    return n;
}

Json BattleModel::evaluate_stars() const
{
    Json out = Json::array();
    Json objs = stage.contains("stars") ? stage["stars"] : Json::array({{{"type", "clear"}}});
    for (auto& o : objs)
    {
        std::string t = S(o, "type", "clear");
        if (t == "clear") out.push_back(true);
        else if (t == "no_ko") out.push_back(players_ko == 0);
        else if (t == "turns") out.push_back(total_rounds <= I(o, "max", 99));
        else if (t == "burst") out.push_back(total_bursts() >= I(o, "min", 1));
        else out.push_back(false);
    }
    while (out.size() < 3) out.push_back(false);
    return out;
}

Json BattleModel::roll_stage_drops()
{
    Json drops = Progression::roll_table({{"rolls", A(stage, "drops")}}, rng);
    for (auto& [id, q] : drops.items()) items_earned[id] = I(items_earned, id, 0) + I(q);
    return drops;
}

Json BattleModel::victory_data() const
{
    return {{"xp", xp_earned}, {"gold", gold_earned}, {"items", items_earned}, {"stars", evaluate_stars()},
            {"bursts", bursts_used}, {"enemies_defeated", enemies_defeated}, {"bosses_defeated", bosses_defeated},
            {"rounds", total_rounds}};
}

// ================================================================== enemy AI
// Each enemy's "ai" block picks a profile: attacker, healer, tank, buffer, debuffer,
// charger or boss (pattern of normal/charge/curse/heal, summons, hp_events, phase2).
// Elites add extra_every. Targeting: random (Provoke-weighted), lowest_hp, highest_atk.
EnemyDecision BattleModel::ai_skill(const CombatantPtr& e, const std::string& skill_id, const Units& foes)
{
    return {"skill", skill_id, choose_target(*e, foes, skill_id)};
}

static CombatantPtr most_injured(const Units& allies)
{
    CombatantPtr best;
    for (auto& a : allies)
        if (a->is_alive() && a->hp_ratio() < 0.6 && (!best || a->hp_ratio() < best->hp_ratio())) best = a;
    return best;
}

EnemyDecision BattleModel::decide(const CombatantPtr& e)
{
    const Json& ai = O(e->def, "ai");
    const Json& skills = O(e->def, "skills");
    Units foes = foes_of(*e);
    ++e->ai_turn;
    ++e->turns_since_summon;
    if (e->is_broken() || S(ai, "profile") == "totem") return {"skip", "", nullptr};   // Broken foes lose their turn
    if (!e->charging_skill.empty())   // 1) a charged attack is always released first
    {
        std::string s = e->charging_skill;
        e->charging_skill.clear();
        e->remove_status("charging");
        return ai_skill(e, s, foes);
    }
    if (!e->pending_charge.empty())   // 2) a phase can start a telegraphed attack at once
    {
        std::string c = e->pending_charge;
        e->pending_charge.clear();
        return {"charge", c, nullptr};
    }
    if (!e->pending_skill.empty())    // 2b) queued reaction (phase skill)
    {
        std::string p = e->pending_skill;
        e->pending_skill.clear();
        return ai_skill(e, p, foes);
    }
    const Json& evs = A(ai, "hp_events");   // 3) one-time HP threshold reactions
    for (int i = 0; i < (int)evs.size(); ++i)
        if (std::find(e->hp_events_done.begin(), e->hp_events_done.end(), i) == e->hp_events_done.end() &&
            e->hp_ratio() < F(evs[i], "below", 0.5))
        {
            e->hp_events_done.push_back(i);
            return ai_skill(e, S(evs[i], "skill"), foes);
        }
    const Json& sm = O(ai, "summon");   // 4) summons
    if (!sm.empty() && e->turns_since_summon >= std::max(I(sm, "every", 3), 1) && can_summon(*e))
    {
        e->turns_since_summon = 0;
        return {"summon", "", nullptr};
    }
    int extra_every = I(ai, "extra_every", 0);   // 5) elite extra skill
    if (extra_every > 0 && skills.contains("extra") && e->ai_turn % extra_every == 0) return ai_skill(e, S(skills, "extra"), foes);

    const std::string& special = e->special_skill;
    std::string profile = S(ai, "profile", "attacker");
    if (profile == "boss")
    {
        Json pattern = ai.contains("pattern") ? ai["pattern"] : Json::array({"normal"});
        Json ph = phases_of(ai);
        for (int i = std::min(e->phase_index, (int)ph.size()) - 1; i >= 0; --i)   // latest phase with its own pattern
            if (ph[i].contains("pattern")) { pattern = ph[i]["pattern"]; break; }
        std::string step = pattern.empty() ? "normal" : S(pattern[e->pattern_index % pattern.size()]);
        ++e->pattern_index;
        if (step == "charge" && !special.empty()) return {"charge", special, nullptr};
        if (!DB.skill(step).empty()) return ai_skill(e, step, foes);   // any skill id can be a pattern step
        if (step == "curse" && ai.contains("curse")) return ai_skill(e, S(ai, "curse"), foes);
        if (step == "heal" && ai.contains("heal") && most_injured(allies_of(*e))) return ai_skill(e, S(ai, "heal"), foes);
    }
    else if (profile == "charger")
    {
        if (!special.empty() && e->ai_turn % std::max(I(ai, "charge_every", 3), 1) == 0) return {"charge", special, nullptr};
    }
    else if (profile == "healer")
    {
        if (!special.empty() && e->last_action != special && most_injured(allies_of(*e))) return ai_skill(e, special, foes);
    }
    else if (profile == "tank")
    {
        if (!special.empty() && e->ai_turn % 3 == 1 && !e->has_status("taunt")) return ai_skill(e, special, foes);
    }
    else if (profile == "buffer")
    {
        bool anyone = false;
        for (auto& a : alive(allies_of(*e))) anyone = anyone || a->has_status("atk_up");
        if (!special.empty() && !anyone && rng.randf() < std::max(e->skill_chance, 0.5)) return ai_skill(e, special, foes);
    }
    else if (!special.empty() && rng.randf() < e->skill_chance)   // debuffer + attacker
        return ai_skill(e, special, foes);
    return ai_skill(e, e->normal_skill, foes);
}

CombatantPtr BattleModel::choose_target(const Combatant& enemy, const Units& foes, const std::string& skill_id)
{
    Units live = alive(foes);
    if (live.empty()) return nullptr;
    auto weighted = [&]() {
        double total = 0;
        for (auto& f : live) total += f->taunt_weight();
        double roll = rng.randf() * total;
        for (auto& f : live)
        {
            roll -= f->taunt_weight();
            if (roll <= 0) return f;
        }
        return live.back();
    };
    for (auto& f : live)
        if (f->has_status("taunt")) return weighted();   // a provoking hero overrides smart targeting
    std::string mode = S(O(enemy.def, "ai"), "targeting", "random");
    if (mode == "lowest_hp")
    {
        std::stable_sort(live.begin(), live.end(), [](auto& a, auto& b) { return a->hp_ratio() < b->hp_ratio(); });
        return live[0];
    }
    if (mode == "highest_atk")
    {
        std::string st;   // prefer a strong hero not already cursed by this skill
        for (auto& e : A(DB.skill(skill_id), "effects"))
            if (S(e, "type") == "status") st = S(e, "status");
        std::stable_sort(live.begin(), live.end(), [](auto& a, auto& b) { return a->get_stat("atk") > b->get_stat("atk"); });
        for (auto& f : live)
            if (st.empty() || !f->has_status(st)) return f;
        return live[0];
    }
    return weighted();
}
