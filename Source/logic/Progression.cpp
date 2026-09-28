#include "Progression.h"
#include <cmath>

std::string fmt_number(long long n)
{
    std::string s = std::to_string(n < 0 ? -n : n), out;
    for (size_t i = 0; i < s.size(); ++i)
    {
        if (i && (s.size() - i) % 3 == 0) out += ',';
        out += s[i];
    }
    return (n < 0 ? "-" : "") + out;
}

namespace Progression
{
static const char* STAT_KEYS[] = {"hp", "atk", "def", "rec", "spd"};

int xp_to_next(int level)
{
    const Json& c = O(DB.progression, "unit_xp_curve");
    return (int)std::round(F(c, "base", 50) * std::pow(std::max(level, 1), F(c, "exponent", 1.5)));
}

int rank_xp_to_next(int rank)
{
    const Json& c = O(DB.progression, "rank_xp_curve");
    return (int)std::round(F(c, "base", 60) * std::pow(std::max(rank, 1), F(c, "exponent", 1.35)));
}

Json unit_stats(const Json& def, int level)
{
    Json out = Json::object();
    for (auto k : STAT_KEYS)
        out[k] = I(O(def, "base_stats"), k, 0) + I(O(def, "growth"), k, 0) * (std::max(level, 1) - 1);
    return out;
}

Json add_unit_xp(Json& u, int amount)
{
    const Json& def = DB.character(S(u, "char_id"));
    int max_level = I(def, "max_level", 20);
    Json ups = Json::array();
    u["exp"] = I(u, "exp", 0) + std::max(amount, 0);
    while (I(u, "level", 1) < max_level && I(u, "exp", 0) >= xp_to_next(I(u, "level", 1)))
    {
        u["exp"] = I(u, "exp", 0) - xp_to_next(I(u, "level", 1));
        Json before = unit_stats(def, I(u, "level", 1));
        u["level"] = I(u, "level", 1) + 1;
        Json after = unit_stats(def, I(u, "level", 1));
        Json gains = Json::object();
        for (auto k : {"hp", "atk", "def", "rec"}) gains[k] = I(after[k]) - I(before[k]);
        ups.push_back({{"level", u["level"]}, {"gains", gains}});
    }
    if (I(u, "level", 1) >= max_level) u["exp"] = 0;
    return ups;
}

int train_cost(const Json& u)
{
    int remaining = xp_to_next(I(u, "level", 1)) - I(u, "exp", 0);
    return (int)std::ceil(std::max(remaining, 1) * F(DB.progression, "train_gold_per_xp", 1.5));
}

Json enemy_stats(const Json& d, int level, double hp_scale)
{
    const Json& b = O(d, "base_stats");
    const Json& sc = O(DB.progression, "enemy_scaling");
    double l = std::max(level, 1) - 1;
    auto r = [](double v) { return (int)std::round(v); };
    return {{"hp", r(F(b, "hp", 100) * (1.0 + F(sc, "hp", 0.22) * l) * hp_scale)},
            {"atk", r(F(b, "atk", 30) * (1.0 + F(sc, "atk", 0.14) * l))},
            {"def", r(F(b, "def", 20) * (1.0 + F(sc, "def", 0.1) * l))},
            {"rec", 0},
            {"spd", r(F(b, "spd", 40) * (1.0 + F(sc, "spd", 0.03) * l))}};
}

int enemy_xp(const Json& d, int level)
{
    const Json& sc = O(DB.progression, "enemy_scaling");
    return (int)std::round(F(O(d, "rewards"), "xp", 10) * (1.0 + F(sc, "xp", 1.0) * (std::max(level, 1) - 1)));
}

Json roll_enemy_loot(const Json& d, int level, Rng& rng)
{
    const Json& sc = O(DB.progression, "enemy_scaling");
    const Json& gr = at(O(d, "rewards"), "gold");
    int lo = gr.is_array() ? I(gr[0]) : 5, hi = gr.is_array() ? I(gr[1]) : 10;
    int gold = rng.randi_range(lo, hi);
    gold = (int)std::round(gold * (1.0 + F(sc, "gold", 0.35) * (std::max(level, 1) - 1)));
    return {{"gold", gold}, {"items", roll_table(at(d, "drop_table"), rng)}};
}

Json resolve_table(const Json& t)
{
    if (t.is_string()) return O(DB.drop_tables, S(t));
    if (t.is_array()) return {{"rolls", t}};
    if (t.is_object()) return t;
    return Json::object();
}

Json roll_table(const Json& table, Rng& rng)
{
    Json t = resolve_table(table);
    Json drops = Json::object();
    for (auto& e : A(t, "guaranteed"))
    {
        int q = rng.randi_range(I(e, "min", 1), I(e, "max", 1));
        drops[S(e, "item")] = I(drops, S(e, "item"), 0) + q;
    }
    for (auto& e : A(t, "rolls"))
        if (rng.randf() < F(e, "chance", 0.0))
        {
            int q = rng.randi_range(I(e, "min", 1), I(e, "max", 1));
            drops[S(e, "item")] = I(drops, S(e, "item"), 0) + q;
        }
    return drops;
}

std::vector<std::string> table_items(const Json& table)
{
    Json t = resolve_table(table);
    std::vector<std::string> out;
    for (auto key : {"guaranteed", "rolls"})
        for (auto& e : A(t, key))
            if (std::find(out.begin(), out.end(), S(e, "item")) == out.end()) out.push_back(S(e, "item"));
    return out;
}

int item_xp(const std::string& item_id, const Json& def)
{
    const Json& it = DB.item(item_id);
    int xp = I(it, "xp", 0);
    if (xp > 0 && !S(it, "element").empty() && S(it, "element") == S(def, "element"))
        xp = (int)std::round(xp * (1.0 + DB.balancef("training", "element_bonus", 0.5)));
    return xp;
}

int training_gold(int xp) { return (int)std::ceil(xp * DB.balancef("training", "gold_per_xp", 0.5)); }

int xp_to_cap(const Json& u)
{
    const Json& def = DB.character(S(u, "char_id"));
    int total = -I(u, "exp", 0);
    for (int l = I(u, "level", 1); l < I(def, "max_level", 20); ++l) total += xp_to_next(l);
    return std::max(total, 0);
}

static Json burst_steps()
{
    const Json& s = DB.balance("burst_levels", "xp");
    return s.is_array() ? s : Json::array({0, 4, 10, 18, 30});
}

int burst_level_for_xp(int xp)
{
    Json steps = burst_steps();
    int lvl = 1;
    for (size_t i = 0; i < steps.size(); ++i)
        if (xp >= I(steps[i])) lvl = (int)i + 1;
    return std::clamp(lvl, 1, I(DB.balance("burst_levels", "max"), 5));
}

int burst_xp_for_level(int level)
{
    Json steps = burst_steps();
    return I(steps[std::clamp(level - 1, 0, (int)steps.size() - 1)]);
}

Json scaled_burst(const Json& skill, int level)
{
    Json s = skill;
    int n = std::max(level - 1, 0);
    if (n == 0) return s;
    const Json& b = O(skill, "level_bonus");
    if (b.contains("power") && F(s, "power", 0) > 0) s["power"] = F(s, "power", 0) * (1.0 + F(b, "power", 0) * n);
    int extra_turns = 0;
    for (auto& a : A(b, "duration_at"))
        if (level >= I(a)) ++extra_turns;
    if (s.contains("effects"))
        for (auto& e : s["effects"])
        {
            std::string t = S(e, "type");
            if (t == "heal") e["percent_max_hp"] = F(e, "percent_max_hp", 0) + F(b, "heal", 0) * n;
            else if (t == "shield") e["percent_caster_hp"] = F(e, "percent_caster_hp", 0) + F(b, "shield", 0) * n;
            else if (t == "burst") e["value"] = F(e, "value", 0) + F(b, "burst", 0) * n;
            else if (t == "status")
            {
                if (e.contains("value") && F(e, "value", 0) > 0 && S(e, "status") != "taunt")
                    e["value"] = F(e, "value", 0) + F(b, "value", 0) * n;
                e["chance"] = std::min(1.0, F(e, "chance", 1.0) + F(b, "chance", 0) * n);
                e["duration"] = I(e, "duration", 1) + extra_turns;
            }
        }
    return s;
}

double burst_cost(const Json& skill, int level)
{
    return std::max(60.0, DB.balancef("burst", "max", 100) - F(O(skill, "level_bonus"), "gauge", 0) * std::max(level - 1, 0));
}

std::string burst_level_text(const Json& skill)
{
    const Json& b = O(skill, "level_bonus");
    std::vector<std::string> parts;
    auto pct = [&](const char* k) { return std::to_string((int)std::round(F(b, k, 0) * 100)); };
    if (b.contains("power")) parts.push_back("+" + pct("power") + "% damage");
    if (b.contains("heal")) parts.push_back("+" + pct("heal") + "% healing");
    if (b.contains("shield")) parts.push_back("+" + pct("shield") + "% shield");
    if (b.contains("value")) parts.push_back("stronger effects");
    if (b.contains("chance")) parts.push_back("+" + pct("chance") + "% effect chance");
    if (b.contains("burst")) parts.push_back("+" + std::to_string(I(b, "burst", 0)) + " Burst for allies");
    if (b.contains("gauge")) parts.push_back("-" + std::to_string(I(b, "gauge", 0)) + " gauge cost");
    if (b.contains("duration_at"))
    {
        std::string lv;
        for (auto& a : A(b, "duration_at")) lv += (lv.empty() ? "" : "/") + std::to_string(I(a));
        parts.push_back("+1 turn at Lv." + lv);
    }
    if (parts.empty()) return "";
    std::string out = "Per level: ";
    for (size_t i = 0; i < parts.size(); ++i) out += (i ? ", " : "") + parts[i];
    return out;
}

int unit_power(const Json& u)
{
    Json st = unit_stats(DB.character(S(u, "char_id")), I(u, "level", 1));
    const Json& w = O(DB.progression, "power");
    double p = I(st["hp"]) * F(w, "hp", 0.1) + I(st["atk"]) * F(w, "atk", 1.0) + I(st["def"]) * F(w, "def", 0.8) +
               I(st["rec"]) * F(w, "rec", 0.5);
    p *= 1.0 + F(w, "burst_level", 0.03) * (I(u, "burst_level", 1) - 1);
    return (int)std::round(p);
}
}  // namespace Progression

namespace SummonSystem
{
Json rates(const Json& banner)
{
    const Json& raw = O(banner, "rates");
    double total = 0;
    for (auto& [k, v] : raw.items()) total += std::max(0.0, F(v));
    if (total <= 0) return {{"3", 1.0}};
    Json out = Json::object();
    for (auto& [k, v] : raw.items()) out[k] = std::max(0.0, F(v)) / total;
    return out;
}

Json pool_by_rarity(const Json& banner)
{
    Json out = Json::object();
    for (auto& cid : A(banner, "pool"))
    {
        const Json& d = DB.character(S(cid));
        if (d.empty()) continue;
        out[std::to_string(I(d, "rarity", 3))].push_back(S(cid));
    }
    return out;
}

static double available_weight(const Json& rr, const Json& pool)
{
    double s = 0;
    for (auto& [r, v] : rr.items())
        if (pool.contains(r) && !pool[r].empty()) s += F(v);
    return s > 0 ? s : 1.0;
}

Json hero_rates(const Json& banner)
{
    Json rr = rates(banner), pool = pool_by_rarity(banner), out = Json::object();
    double norm = available_weight(rr, pool);
    for (auto& [r, ids] : pool.items())
        for (auto& cid : ids) out[S(cid)] = F(rr, r, 0) / norm / double(ids.size());
    return out;
}

std::string roll(const Json& banner, Rng& rng)
{
    Json rr = rates(banner), pool = pool_by_rarity(banner);
    if (pool.empty()) return "";
    std::vector<std::string> keys;
    for (auto& [k, v] : rr.items()) keys.push_back(k);
    std::sort(keys.begin(), keys.end());
    double pick = rng.randf() * available_weight(rr, pool);
    std::string chosen;
    for (auto& r : keys)
    {
        if (!pool.contains(r) || pool[r].empty()) continue;
        chosen = r;
        pick -= F(rr, r, 0);
        if (pick < 0) break;
    }
    if (chosen.empty()) chosen = pool.begin().key();
    const Json& ids = pool[chosen];
    return S(ids[rng.randi_range(0, (int)ids.size() - 1)]);
}
}  // namespace SummonSystem
