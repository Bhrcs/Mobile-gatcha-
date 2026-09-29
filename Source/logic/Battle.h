#pragma once
// Rules-only battle state (no rendering): Combatant (HP, Burst, statuses, derived
// stats), the damage formula, data-driven enemy AI and BattleModel (waves, turn
// order, action planning and resolution). The battle scene animates the results;
// tests and the balance simulator drive the model directly.
#include "Database.h"
#include "Progression.h"
#include <memory>

struct Combatant;
using CombatantPtr = std::shared_ptr<Combatant>;
using Units = std::vector<CombatantPtr>;

struct Combatant
{
    std::string id, uid, display_name, element = "fire";
    int level = 1, slot = 0;
    bool is_player = false, is_boss = false;
    Json def = Json::object();
    Json base_stats = {{"hp", 1}, {"atk", 1}, {"def", 1}, {"rec", 0}, {"spd", 1}};
    int max_hp = 1, hp = 1;
    double burst = 0, burst_max = 100;
    std::string normal_skill, burst_skill, special_skill;
    double skill_chance = 0.3;
    bool acted = false, guarding = false;
    Json statuses = Json::array();   // [{id, value, turns}] (shield value = HP it still absorbs)

    int burst_level = 1;
    bool is_elite = false, summoned = false, counted = false;
    int summon_index = 0;
    Json passive_stats = Json::array();
    double heal_received_up = 0, damage_taken_down = 0, burst_gain_mult = 1, regen_aura = 0, crit_bonus = 0,
           guard_bonus = 0, bonus_vs_low_hp = 0, low_hp_threshold = 0.5, bonus_vs_debuffed = 0, enrage = 0;
    int last_absorbed = 0;

    // enemy AI state
    int ai_turn = 0, pattern_index = 0, turns_since_summon = 0;
    std::string charging_skill, pending_skill, pending_charge, last_action;
    bool phase2 = false;             // reached at least one phase (kept for older callers)
    int phase_index = 0, charge_damage = 0;
    std::vector<int> hp_events_done;

    // Break Gauge (bosses/elites with a "break" block): hits drain it; at 0 the foe is Broken.
    double break_max = 0, break_value = 0;
    std::string break_weak;
    Json status_hits = Json::object();   // times each status landed (boss diminishing returns)

    Signal<int, int> hp_changed;
    Signal<double, double> burst_changed;
    Signal<> statuses_changed, died, break_changed;

    static CombatantPtr from_player_unit(const Json& unit, int slot);
    static CombatantPtr from_enemy(const std::string& enemy_id, int level, int slot, double hp_scale = 1.0);

    void apply_aura(const Json& e);
    void apply_stat_bonus(const std::string& stat, double value);
    Json skill_data(const std::string& skill_id);
    bool is_alive() const { return hp > 0; }
    bool can_act() const { return is_alive() && !acted; }
    bool burst_ready() const { return is_alive() && !burst_skill.empty() && burst >= burst_max; }
    double hp_ratio() const { return double(hp) / double(std::max(max_hp, 1)); }
    double get_stat(const std::string& stat) const;
    double damage_bonus_vs(const Combatant& t) const;
    bool has_negative_status() const;
    double status_resist(const std::string& id) const;
    std::vector<std::string> dispel(int count);
    bool is_broken() const { return has_status("broken"); }
    std::string role() const;
    int shield_amount() const;
    void add_shield(int amount, int turns) { add_status("shield", amount, turns); }
    void remove_status(const std::string& id);
    double damage_reduction() const;
    double taunt_weight() const;
    int take_damage(int amount);
    int heal(int amount);
    void add_burst(double amount);
    void reset_burst();
    void add_status(const std::string& id, double value, int turns);
    bool has_status(const std::string& id) const;
    std::vector<std::string> cleanse(int count);
    Json tick_statuses();   // [{type: dot|hot, status, amount}]

private:
    Json _skill_cache = Json::object();
};

struct HitResult { int dealt = 0, absorbed = 0; bool killed = false, skipped = true, broke = false, interrupted = false; };
struct PlanTarget
{
    CombatantPtr unit;
    std::vector<int> hits;
    bool crit = false, landed = false, burst_given = false;
    std::string tag;   // "", WEAK, RESIST
    int total = 0, dealt = 0, absorbed = 0;
    double break_per_hit = 0;
};
struct Plan
{
    std::string skill_id;
    Json skill;
    CombatantPtr user, ally_target;
    std::vector<PlanTarget> targets;
    bool is_burst = false;
};
struct BattleEvent { std::string type; CombatantPtr unit; int amount = 0; std::string status; };
struct EnemyDecision { std::string type, skill_id; CombatantPtr target; };   // skill | charge | summon | skip

namespace DamageCalculator
{
struct Result { int total; std::vector<int> hits; bool crit; double element_mult; std::string tag; };
Result calculate(const Combatant& attacker, const Combatant& target, const Json& skill, Rng& rng);
std::vector<int> split_hits(int total, int hits, const Json& weights = Json::array());
int heal_amount(const Combatant& caster, const Combatant& target, const Json& effect);
double break_amount(const Combatant& attacker, const Combatant& target, const Json& skill);
}  // namespace DamageCalculator

class BattleModel
{
public:
    static constexpr int MAX_ENEMIES_ALIVE = 4, MAX_SUMMONED = 2;
    Json stage = Json::object(), waves = Json::array();
    int wave_index = -1, round_number = 0;
    Units players, enemies;
    Rng rng;
    int xp_earned = 0, gold_earned = 0, enemies_defeated = 0, bosses_defeated = 0, total_rounds = 0, players_ko = 0;
    Json items_earned = Json::object(), bursts_used = Json::object();
    Signal<CombatantPtr> enemy_defeated;
    Signal<int> wave_spawned;

    void setup(const std::string& stage_id, const Json& party_units, int seed = -1);
    std::string leader_element() const { return players.empty() ? "fire" : players[0]->element; }
    int wave_count() const { return (int)waves.size(); }
    bool has_next_wave() const { return wave_index + 1 < (int)waves.size(); }
    Units& advance_wave();
    void start_player_phase();
    bool players_can_act() const;
    CombatantPtr first_ready_player() const;
    static Units alive(const Units& list);
    bool all_enemies_dead() const { return alive(enemies).empty(); }
    bool all_players_dead() const { return alive(players).empty(); }
    Units enemy_turn_order() const;
    std::vector<BattleEvent> end_round();
    int apply_dot(const CombatantPtr& u, int amount);
    int apply_hot(const CombatantPtr& u, int amount) { return u->heal(amount); }
    Units& allies_of(const Combatant& c) { return c.is_player ? players : enemies; }
    Units& foes_of(const Combatant& c) { return c.is_player ? enemies : players; }
    void gain_burst(Combatant& u, double amount) { u.add_burst(amount * u.burst_gain_mult); }
    void guard(Combatant& u);
    Plan plan_action(const CombatantPtr& user, const std::string& skill_id, CombatantPtr target, bool use_burst = false);
    HitResult apply_hit(Plan& plan, int target_index, int hit_index);
    std::vector<BattleEvent> finish_action(Plan& plan);
    std::vector<BattleEvent> resolve_instant(Plan& plan);
    void begin_charge(Combatant& enemy, const std::string& skill_id);
    Json check_phase(Combatant& enemy);   // next boss phase reached this turn (announce, summon, charge, ...)
    Units summon_minions(Combatant& boss, const Json& sm = Json());
    bool can_summon(const Combatant& boss, const Json& sm = Json()) const;
    void refresh_auras();                 // totem-style auras ("aura" on an enemy buffs every boss)
    int total_bursts() const;
    Json evaluate_stars() const;
    Json roll_stage_drops();
    Json victory_data() const;
    EnemyDecision decide(const CombatantPtr& enemy);   // EnemyAI

    CombatantPtr choose_target(const Combatant& enemy, const Units& foes, const std::string& skill_id = "");

private:
    void apply_team_bonuses();
    void wave_recovery();
    PlanTarget plan_target(const Combatant& user, const CombatantPtr& target, const Json& skill);
    bool check_death(const CombatantPtr& u);
    void on_break(Combatant& u);
    void on_enemy_killed(const CombatantPtr& e);
    int free_slot() const;
    EnemyDecision ai_skill(const CombatantPtr& e, const std::string& skill_id, const Units& foes);
};
