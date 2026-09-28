#include "Database.h"
#include "Platform.h"

Database& Database::get()
{
    static Database db;
    return db;
}

Json Database::read(const std::string& path)
{
    std::string text = Platform::readText(path);
    if (text.empty())
    {
        load_errors.push_back("Missing data file: " + path);
        return Json::object();
    }
    Json j = Json::parse(text, nullptr, false);
    if (!j.is_object())
    {
        load_errors.push_back("Invalid JSON in " + path);
        return Json::object();
    }
    return j;
}

Json Database::load_folder(const std::string& folder)
{
    Json out = Json::object();
    for (auto& f : A(_manifest, folder))
    {
        Json d = read("data/" + folder + "/" + S(f));
        if (d.contains("id"))
            out[S(d["id"])] = d;
        else
            load_errors.push_back("Data file without id: " + folder + "/" + S(f));
    }
    return out;
}

void Database::reload()
{
    load_errors.clear();
    _manifest = read("data/manifest.json");
    characters = load_folder("characters");
    enemies = load_folder("enemies");
    skills = Json::object();
    for (auto& f : A(_manifest, "skills"))   // skills are merged from several files
    {
        Json d = read("data/skills/" + S(f));   // (never range-for over a temporary's items())
        for (auto& [k, v] : d.items())
            if (k.rfind("_", 0) != 0) skills[k] = v;
    }
    items = read("data/items/items.json");
    statuses = read("data/statuses.json");
    element_config = read("data/elements.json");
    elements = O(element_config, "elements");
    progression = read("data/progression.json");
    hints = read("data/tutorial_hints.json");
    drop_tables = read("data/drop_tables.json");
    summon = read("data/summon.json");
    missions = read("data/missions.json");
    login_rewards = read("data/login_rewards.json");
    load_worlds();
    validate();
    for (auto& e : load_errors) Platform::log("DATA ERROR: " + e);
}

void Database::load_worlds()
{
    worlds = Json::object();
    towers = Json::object();
    stages = Json::object();
    world_order.clear();
    tower_order.clear();
    stage_order.clear();
    std::vector<Json> story;
    Json story_files = load_folder("stages"), tower_files = load_folder("towers");
    for (auto& [k, w] : story_files.items()) story.push_back(w);
    std::stable_sort(story.begin(), story.end(), [](const Json& a, const Json& b) { return I(a, "order", 0) < I(b, "order", 0); });
    for (auto& w : story)
    {
        std::string wid = S(w["id"]);
        for (auto& st : w["stages"]) st["world_id"] = wid;
        worlds[wid] = w;
        world_order.push_back(wid);
        for (auto& st : w["stages"])
        {
            stages[S(st["id"])] = st;
            stage_order.push_back(S(st["id"]));
        }
    }
    for (auto& [k, t] : tower_files.items())
    {
        Json tw = t;
        for (auto& fl : tw["stages"]) fl["world_id"] = tw["id"];
        for (auto& fl : tw["stages"]) stages[S(fl["id"])] = fl;
        towers[k] = tw;
        tower_order.push_back(k);
    }
    std::sort(tower_order.begin(), tower_order.end());
}

void Database::validate()
{
    for (auto& [id, c] : characters.items())
    {
        for (auto key : {"normal_attack", "burst"})
            if (!skills.contains(S(c, key))) load_errors.push_back(id + ": unknown skill " + S(c, key));
        const Json& evo = at(c, "evolution");
        if (evo.is_object())
        {
            if (!characters.contains(S(evo, "into"))) load_errors.push_back(id + ": unknown evolution " + S(evo, "into"));
            for (auto& [m, q] : O(evo, "materials").items())
                if (!items.contains(m)) load_errors.push_back(id + ": unknown material " + m);
        }
    }
    for (auto& [id, e] : enemies.items())
    {
        for (auto& [k, s] : O(e, "skills").items())
            if (!skills.contains(S(s))) load_errors.push_back(id + ": unknown skill " + S(s));
        const Json& dt = at(e, "drop_table");
        if (dt.is_string() && !drop_tables.contains(S(dt))) load_errors.push_back(id + ": unknown drop table " + S(dt));
    }
    for (auto& [sid, st] : stages.items())
    {
        for (auto& wave : A(st, "waves"))
            for (auto& sp : wave)
            {
                std::vector<std::string> ids{S(sp, "enemy")};
                if (sp.contains("enemy_by_leader_element"))
                {
                    ids.clear();
                    for (auto& [k, v] : sp["enemy_by_leader_element"].items()) ids.push_back(S(v));
                }
                for (auto& eid : ids)
                    if (!enemies.contains(eid)) load_errors.push_back(sid + ": unknown enemy " + eid);
            }
        for (auto& d : A(st, "drops"))
            if (!items.contains(S(d, "item"))) load_errors.push_back(sid + ": unknown drop " + S(d, "item"));
    }
    for (auto& fid : A(O(O(summon, "banners"), "standard"), "pool"))
        if (!characters.contains(S(fid))) load_errors.push_back("summon pool: unknown hero " + S(fid));
}

Json Database::family_forms(std::string family) const
{
    if (characters.contains(family)) family = S(characters[family], "family", family);
    for (auto& [id, c] : characters.items())
        if (S(c, "family") == family)
            return c.contains("forms") ? c["forms"] : Json::array({id});
    return Json::array();
}

std::vector<std::string> Database::family_ids() const
{
    static const std::vector<std::string> order{"kael", "rhea", "voss", "seraphine", "mira", "corin",
                                                "nerys", "aldric", "thorne", "wren", "faye", "gorran"};
    auto idx = [&](const std::string& f) {
        auto it = std::find(order.begin(), order.end(), f);
        return it == order.end() ? 999 : int(it - order.begin());
    };
    std::vector<std::string> out;
    std::vector<std::string> seen;
    for (auto& [id, c] : characters.items())
    {
        std::string fam = S(c, "family", id);
        if (std::find(seen.begin(), seen.end(), fam) == seen.end() && I(c, "form_index", 0) == 0)
        {
            seen.push_back(fam);
            out.push_back(id);
        }
    }
    std::sort(out.begin(), out.end(), [&](auto& a, auto& b) {
        int ia = idx(S(characters[a], "family")), ib = idx(S(characters[b], "family"));
        return ia != ib ? ia < ib : a < b;
    });
    return out;
}

std::string Database::item_name(const std::string& id) const { return S(item(id), "name", capitalize(id)); }

bool Database::stage_has_elite(const std::string& id) const
{
    for (auto& wave : A(stage(id), "waves"))
        for (auto& e : wave)
            if (B(enemy(S(e, "enemy")), "elite", false)) return true;
    return false;
}

bool Database::is_tower_stage(const std::string& id) const { return towers.contains(S(stage(id), "world_id")); }

std::vector<std::string> Database::starter_ids() const
{
    std::vector<std::string> out;
    for (auto& [id, c] : characters.items())
        if (B(c, "starter", false)) out.push_back(id);
    static const std::vector<std::string> order{"kael_emberclaw", "mira_tidesong", "thorne_mossguard"};
    std::sort(out.begin(), out.end(), [&](auto& a, auto& b) {
        return std::find(order.begin(), order.end(), a) < std::find(order.begin(), order.end(), b);
    });
    return out;
}

std::string Database::element_name(const std::string& e) const { return S(O(elements, e), "name", capitalize(e)); }
std::string Database::element_color(const std::string& e) const { return S(O(elements, e), "color", "#cccccc"); }

double Database::element_multiplier(const std::string& attacker, const std::string& defender) const
{
    if (contains(A(O(elements, attacker), "strong_against"), defender)) return F(element_config, "strong_multiplier", 1.25);
    if (contains(A(O(elements, defender), "strong_against"), attacker)) return F(element_config, "weak_multiplier", 0.75);
    return 1.0;
}

const Json& Database::sprite_meta(const std::string& path)
{
    std::string p = res(path);
    if (!_meta_cache.contains(p)) _meta_cache[p] = read(p);
    return _meta_cache[p];
}
