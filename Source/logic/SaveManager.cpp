#include "SaveManager.h"
#include "Database.h"
#include "Platform.h"
#include <cmath>

SaveManager& SaveManager::get()
{
    static SaveManager s;
    return s;
}

SaveManager::SaveManager()
{
    save_path = Platform::writablePath() + "cinderbound_save.json";
    settings_path = Platform::writablePath() + "cinderbound_settings.json";
}

Json SaveManager::default_profile() const
{
    return Json::parse(R"({
      "version": 2, "starter_id": "",
      "player": {"name": "Wayfarer", "rank": 1, "rank_xp": 0, "gold": 0, "gems": 0, "soul_shards": 0,
                 "energy": 20, "energy_ts": 0, "play_seconds": 0, "created": 0},
      "units": [], "next_uid": 1, "party": [], "inventory": {},
      "stages": {"cleared": [], "unlocked": [], "stars": {}, "clears": {}},
      "unlocks": {"granted": [], "announced": []}, "codex": [],
      "tutorial": {"intro_seen": false, "hints_seen": [], "coach_done": []},
      "stats": {"battles_won": 0, "battles_lost": 0, "bosses_defeated": 0, "enemies_defeated": 0, "summons": 0},
      "missions": {"daily_key": "", "daily": {}, "daily_claimed": [], "chest_claimed": false,
                   "weekly_key": "", "weekly": {}, "weekly_claimed": []},
      "login": {"last_date": "", "day_index": 0, "total": 0},
      "summon": {"history": [], "total": 0, "seen": false}})");
}

Json SaveManager::default_settings() const
{
    return {{"master_volume", 0.8}, {"music_volume", 0.6}, {"sfx_volume", 0.8}, {"screen_shake", true},
            {"fullscreen", false},  {"battle_speed", 1.0}, {"battle_effects", true}, {"damage_numbers", true},
            {"auto_battle", false}, {"reduce_motion", false}, {"haptics", true},  {"safe_area", 0},
            {"unit_sort", "recent"}, {"unit_sort_desc", true}, {"unit_filter", ""}};
}

bool SaveManager::has_save() const
{
    return Platform::fileExists(save_path) || Platform::fileExists(save_path + ".bak");
}

Json SaveManager::load_profile()
{
    Json data = read_dict(save_path);
    if (!data.empty())
    {
        last_load_status = "ok";
        return sanitize_profile(data);
    }
    Json backup = read_dict(save_path + ".bak");
    if (!backup.empty())
    {
        last_load_status = "recovered_backup";
        return sanitize_profile(backup);
    }
    last_load_status = Platform::fileExists(save_path) ? "corrupted" : "missing";
    return Json::object();
}

bool SaveManager::save_profile(const Json& profile)
{
    return write_atomic(save_path, sanitize_profile(profile, false).dump(1, '\t'));
}

void SaveManager::delete_profile()
{
    for (auto p : {save_path, save_path + ".bak", save_path + ".tmp"}) Platform::removeFile(p);
}

Json SaveManager::load_settings()
{
    Json s = default_settings();
    Json data = read_dict(settings_path);
    for (auto& [k, v] : s.items())
    {
        const Json& d = at(data, k);
        if (d.is_number() || d.is_boolean() || (d.is_string() && v.is_string())) v = d;
    }
    for (auto k : {"master_volume", "music_volume", "sfx_volume"}) s[k] = std::clamp(F(s[k], 0.8), 0.0, 1.0);
    s["battle_speed"] = F(s["battle_speed"], 1) >= 1.5 ? 2.0 : 1.0;
    s["safe_area"] = std::clamp(I(s["safe_area"]), 0, 3);
    for (auto k : {"screen_shake", "battle_effects", "damage_numbers", "auto_battle", "reduce_motion", "haptics",
                   "unit_sort_desc", "fullscreen"})
        s[k] = B(s[k]);
    return s;
}

void SaveManager::save_settings(const Json& s) { write_atomic(settings_path, s.dump(1, '\t')); }

int SaveManager::max_energy_for_rank(int rank) const
{
    const Json& e = O(DB.progression, "energy");
    return std::min(I(e, "base_max", 20) + (int)std::floor((rank - 1) * F(e, "per_rank", 0.5)), I(e, "cap", 60));
}

// ------------------------------------------------------------------ validation / migration
Json SaveManager::sanitize_profile(const Json& data, bool record_notes)
{
    int version = I(data, "version", 1);
    if (record_notes) migration_notes.clear();
    Json p = default_profile();
    p["starter_id"] = DB.has_character(S(data, "starter_id")) ? S(data, "starter_id") : "";

    const Json& player = O(data, "player");
    Json& pl = p["player"];
    std::string name = S(player, "name", "Wayfarer");
    name.erase(0, name.find_first_not_of(" \t"));
    name.erase(name.find_last_not_of(" \t") + 1);
    pl["name"] = name.empty() ? "Wayfarer" : name.substr(0, 16);
    pl["rank"] = std::clamp(I(player, "rank", 1), 1, I(DB.progression, "rank_max", 99));
    pl["rank_xp"] = std::max(I(player, "rank_xp", 0), 0);
    pl["gold"] = std::clamp(I(player, "gold", 0), 0, 999999999);
    pl["gems"] = std::clamp(I(player, "gems", 0), 0, 9999999);
    pl["soul_shards"] = std::clamp(I(player, "soul_shards", 0), 0, 9999999);
    int emax = max_energy_for_rank(I(pl["rank"]));
    pl["energy"] = player.contains("energy") ? std::clamp(I(player, "energy", emax), 0, 999) : emax;
    for (auto k : {"energy_ts", "play_seconds", "created"}) pl[k] = std::max(I(player, k, 0), 0);

    const Json& legacy = O(DB.progression, "legacy_items");
    std::vector<std::string> seen;
    int max_uid = 0, clamped = 0;
    int bmax = I(DB.balance("burst_levels", "max"), 5);
    for (auto& u : A(data, "units"))
    {
        if (!u.is_object()) continue;
        std::string cid = S(u, "char_id"), uid = S(u, "uid");
        if (!DB.has_character(cid) || uid.empty() || std::find(seen.begin(), seen.end(), uid) != seen.end()) continue;
        int max_level = I(DB.character(cid), "max_level", 20);
        int lvl = I(u, "level", 1);
        if (lvl > max_level) ++clamped;
        p["units"].push_back({{"uid", uid}, {"char_id", cid}, {"level", std::clamp(lvl, 1, max_level)},
                              {"exp", lvl < max_level ? std::max(I(u, "exp", 0), 0) : 0},
                              {"burst_level", std::clamp(I(u, "burst_level", 1), 1, bmax)},
                              {"burst_xp", std::max(I(u, "burst_xp", 0), 0)}, {"locked", B(u, "locked", false)},
                              {"favorite", B(u, "favorite", false)}, {"new", B(u, "new", false)},
                              {"obtained", std::max(I(u, "obtained", 0), 0)}});
        seen.push_back(uid);
        std::string fam = S(DB.character(cid), "family", cid);
        if (!contains(p["codex"], fam)) p["codex"].push_back(fam);
        if (uid.size() > 1 && uid[0] == 'u' && uid.find_first_not_of("0123456789", 1) == std::string::npos)
            max_uid = std::max(max_uid, std::stoi(uid.substr(1)));
    }
    if (clamped > 0 && record_notes)
        migration_notes.push_back(std::to_string(clamped) +
                                  " hero(es) were above the new level cap and are now at max level, ready to evolve.");
    p["next_uid"] = std::max(I(data, "next_uid", 1), max_uid + 1);
    if (p["units"].empty() && !S(p["starter_id"]).empty())
    {
        p["units"].push_back({{"uid", "u" + std::to_string(I(p["next_uid"]))}, {"char_id", p["starter_id"]}, {"level", 1},
                              {"exp", 0}, {"burst_level", 1}, {"burst_xp", 0}, {"locked", false}, {"favorite", false},
                              {"new", false}, {"obtained", 0}});
        p["next_uid"] = I(p["next_uid"]) + 1;
        seen.push_back(S(p["units"][0]["uid"]));
    }
    for (auto& c : A(data, "codex"))
        if (c.is_string() && !contains(p["codex"], c) && !DB.family_forms(S(c)).empty()) p["codex"].push_back(c);

    int max_party = I(DB.progression, "party_size", 5);
    for (auto& uid : A(data, "party"))
        if (uid.is_string() && std::find(seen.begin(), seen.end(), S(uid)) != seen.end() && !contains(p["party"], uid) &&
            (int)p["party"].size() < max_party)
            p["party"].push_back(uid);
    if (p["party"].empty() && !p["units"].empty()) p["party"].push_back(p["units"][0]["uid"]);

    int stack = I(DB.progression, "inventory_stack_limit", 9999), converted = 0;
    for (auto& [id, q] : O(data, "inventory").items())
    {
        std::string target = S(legacy, id, id);
        if (target != id && DB.items.contains(target)) ++converted;
        int n = std::clamp(I(q), 0, stack);
        if (DB.items.contains(target) && n > 0) p["inventory"][target] = std::clamp(I(p["inventory"], target, 0) + n, 0, stack);
    }
    if (converted > 0 && record_notes) migration_notes.push_back("Old elemental shards were converted into the new Fragments.");
    if (version < 2)
    {
        if (record_notes && !S(p["starter_id"]).empty())
            migration_notes.push_back("Your save was updated for the new update: Energy, Gems, Burst levels and stage stars "
                                      "were added. You also received a set of training wisps.");
        for (auto& [id, q] : O(DB.progression, "starting_items").items()) p["inventory"][id] = I(p["inventory"], id, 0) + I(q);
    }

    const Json& st = O(data, "stages");
    Json& ps = p["stages"];
    for (auto key : {"cleared", "unlocked"})
        for (auto& sid : A(st, key))
            if (sid.is_string() && DB.stages.contains(S(sid)) && !contains(ps[key], sid)) ps[key].push_back(sid);
    for (auto& [sid, arr] : O(st, "stars").items())
        if (DB.stages.contains(sid) && arr.is_array())
        {
            Json out = Json::array();
            for (int i = 0; i < 3; ++i) out.push_back(B(at(arr, i)));
            ps["stars"][sid] = out;
        }
    for (auto& [sid, n] : O(st, "clears").items())
        if (DB.stages.contains(sid)) ps["clears"][sid] = std::max(I(n), 0);
    for (auto& sid : ps["cleared"])
    {
        if (!ps["stars"].contains(S(sid))) ps["stars"][S(sid)] = {true, false, false};
        if (I(ps["clears"], S(sid), 0) < 1) ps["clears"][S(sid)] = 1;
    }
    if (!DB.stage_order.empty() && !contains(ps["unlocked"], DB.stage_order[0])) ps["unlocked"].push_back(DB.stage_order[0]);
    for (auto& sid : Json(ps["cleared"]))
    {
        if (!contains(ps["unlocked"], sid)) ps["unlocked"].push_back(sid);
        for (auto& nx : A(DB.stage(S(sid)), "unlocks"))
            if (!contains(ps["unlocked"], nx)) ps["unlocked"].push_back(nx);
    }

    for (auto key : {"granted", "announced"})
        for (auto& v : A(O(data, "unlocks"), key))
            if (v.is_string() && !contains(p["unlocks"][key], v)) p["unlocks"][key].push_back(v);

    const Json& tut = O(data, "tutorial");
    p["tutorial"]["intro_seen"] = B(tut, "intro_seen", false);
    for (auto key : {"coach_done", "hints_seen"})
        for (auto& v : A(tut, key))
            if (v.is_string() && !contains(p["tutorial"][key], v)) p["tutorial"][key].push_back(v);

    for (auto& [k, v] : p["stats"].items()) v = std::max(I(O(data, "stats"), k, 0), 0);

    const Json& ms = O(data, "missions");
    Json& pm = p["missions"];
    pm["daily_key"] = S(ms, "daily_key");
    pm["weekly_key"] = S(ms, "weekly_key");
    pm["chest_claimed"] = B(ms, "chest_claimed", false);
    for (auto key : {"daily", "weekly"})
        for (auto& [k, v] : O(ms, key).items()) pm[key][k] = std::max(I(v), 0);
    for (auto key : {"daily_claimed", "weekly_claimed"})
        for (auto& v : A(ms, key))
            if (v.is_string() && !contains(pm[key], v)) pm[key].push_back(v);

    const Json& lg = O(data, "login");
    p["login"]["last_date"] = S(lg, "last_date");
    p["login"]["day_index"] = std::max(I(lg, "day_index", 0), 0);
    p["login"]["total"] = std::max(I(lg, "total", 0), 0);

    const Json& sm = O(data, "summon");
    p["summon"]["total"] = std::max(I(sm, "total", 0), 0);
    p["summon"]["seen"] = B(sm, "seen", false);
    for (auto& h : A(sm, "history"))
        if (h.is_object() && DB.has_character(S(h, "id")))
            p["summon"]["history"].push_back({{"id", h["id"]}, {"r", I(h, "r", 3)}, {"new", B(h, "new", false)},
                                              {"shards", I(h, "shards", 0)}, {"t", I(h, "t", 0)}});
    Json& hist = p["summon"]["history"];
    if (hist.size() > 100) hist.erase(hist.begin(), hist.begin() + (hist.size() - 100));
    return p;
}

// ------------------------------------------------------------------ files
Json SaveManager::read_dict(const std::string& path) const
{
    std::string text = Platform::readText(path);
    if (text.find_first_not_of(" \t\r\n") == std::string::npos) return Json::object();
    Json j = Json::parse(text, nullptr, false);
    return j.is_object() ? j : Json::object();
}

bool SaveManager::write_atomic(const std::string& path, const std::string& text) const
{
    std::string tmp = path + ".tmp";
    if (!Platform::writeText(tmp, text)) return false;
    if (Platform::fileExists(path))
    {
        Platform::removeFile(path + ".bak");
        Platform::renameFile(path, path + ".bak");   // keep the last good save
    }
    return Platform::renameFile(tmp, path);
}
