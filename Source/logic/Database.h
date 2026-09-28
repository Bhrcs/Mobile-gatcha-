#pragma once
// Loads every data-driven definition (characters, enemies, skills, stages, items,
// elements, statuses, balance) from Content/data. Nothing here is hard-coded:
// drop a new JSON file into data/characters (and re-run tools/make_manifest.py)
// and the unit becomes available without touching combat code.
#include "Json.h"

// "res://assets/x.png" (Godot-era data paths) -> "assets/x.png"
inline std::string res(const std::string& p) { return p.rfind("res://", 0) == 0 ? p.substr(6) : p; }

class Database
{
public:
    static Database& get();
    void reload();

    Json characters = Json::object(), enemies = Json::object(), skills = Json::object(), items = Json::object(),
         statuses = Json::object(), worlds = Json::object(), towers = Json::object(), stages = Json::object(),
         drop_tables = Json::object(), summon = Json::object(), missions = Json::object(),
         login_rewards = Json::object(), elements = Json::object(), element_config = Json::object(),
         progression = Json::object(), hints = Json::object();
    std::vector<std::string> world_order, tower_order, stage_order, load_errors;

    const Json& character(const std::string& id) const { return O(characters, id); }
    const Json& enemy(const std::string& id) const { return O(enemies, id); }
    const Json& skill(const std::string& id) const { return O(skills, id); }
    const Json& item(const std::string& id) const { return O(items, id); }
    const Json& stage(const std::string& id) const { return O(stages, id); }
    const Json& status(const std::string& id) const { return O(statuses, id); }
    bool has_character(const std::string& id) const { return characters.contains(id); }

    Json family_forms(std::string family) const;
    std::vector<std::string> family_ids() const;
    std::string item_name(const std::string& id) const;
    bool stage_has_elite(const std::string& id) const;
    bool is_tower_stage(const std::string& id) const;
    std::vector<std::string> starter_ids() const;
    const Json& balance(const std::string& section, const std::string& key) const { return at(O(progression, section), key); }
    double balancef(const std::string& section, const std::string& key, double d) const { return F(balance(section, key), d); }

    std::string element_name(const std::string& e) const;
    std::string element_color(const std::string& e) const;   // "#rrggbb"
    double element_multiplier(const std::string& attacker, const std::string& defender) const;
    const Json& sprite_meta(const std::string& path);

private:
    Json read(const std::string& path);
    Json load_folder(const std::string& folder);
    void load_worlds();
    void validate();
    Json _manifest, _meta_cache = Json::object();
};

#define DB Database::get()
