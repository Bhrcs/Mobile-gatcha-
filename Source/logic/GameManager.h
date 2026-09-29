#pragma once
// Owns the live player profile and every progression rule that changes it:
// currencies, energy (offline regen), rank, heroes, squad + leader, training,
// Burst levels, evolution, summoning, stage/tower progress, stars, feature
// unlocks, missions and login rewards. Every change that should persist saves.
// Engine-free: the app layer listens to the signals (and applies settings).
#include "Database.h"
#include "Progression.h"
#include "SaveManager.h"

class GameManager
{
public:
    static GameManager& get();

    Json profile = Json::object();
    Json settings = Json::object();
    std::string current_stage_id;        // stage the next battle scene should load
    std::string last_unlocked_stage;     // highlighted by the stage map
    Rng rng;
    double clock_override = -1;          // test hook: replaces the system clock when >= 0
    std::vector<std::string> pending_migration_notes;

    Signal<> profile_changed, settings_changed;
    Signal<int> gold_changed, gems_changed;
    Signal<int, int> energy_changed;

    void init();                          // load settings (after Database)
    double now() const;
    void tick(double dt);                 // play time + live energy regen signal

    // profile lifecycle
    bool has_profile() const;
    bool can_continue();
    void new_game(const std::string& starter_id);
    bool continue_game();
    void save();

    // units
    std::string add_unit(const std::string& char_id, bool mark_new = true);
    Json& units();
    Json& unit(const std::string& uid);   // null Json when missing (check .is_null())
    bool owns_family(const std::string& family);
    void mark_unit_seen(const std::string& uid);
    void set_unit_flag(const std::string& uid, const std::string& flag, bool on);
    Json unit_stats(const Json& u) const;
    int unit_power(const Json& u) const { return Progression::unit_power(u); }
    int squad_power();

    // squad
    Json party_uids() const;
    Json party_units();                   // copies; mutate through unit(uid)
    int max_party_size() const;
    bool is_in_party(const std::string& uid) const;
    bool toggle_party(const std::string& uid);
    bool set_leader(const std::string& uid);
    bool swap_party_slots(int a, int b);
    std::string leader_uid() const;
    Json leader_skill();

    // training, burst, evolution
    Json preview_training(const std::string& uid, const Json& items);
    Json train_unit_with(const std::string& uid, const Json& items);
    Json add_burst_xp(const std::string& uid, int amount, bool persist = true);
    Json train_burst(const std::string& uid, const std::string& method);
    Json evolution_status(const std::string& uid);
    bool can_evolve(const std::string& uid);
    Json evolve(const std::string& uid);
    Json item_sources(const std::string& item_id);
    std::string stage_label(const std::string& sid) const;

    // currencies & items
    int gold() const;
    int gems() const;
    int soul_shards() const;
    void add_gold(int n, bool persist = true);
    bool spend_gold(int n, bool persist = true);
    void add_gems(int n, bool persist = true);
    bool spend_gems(int n, bool persist = true);
    void add_item(const std::string& id, int qty, bool persist = true);
    bool remove_item(const std::string& id, int qty, bool persist = true);
    int item_count(const std::string& id) const;
    Json grant(const Json& reward, bool persist = true);

    // energy
    int max_energy() const;
    int energy();
    int energy_seconds_to_next();
    bool spend_energy(int n);
    int stage_energy(const std::string& sid) const { return I(DB.stage(sid), "energy", 0); }

    // progress
    int rank() const;
    bool is_stage_unlocked(const std::string& sid) const;
    bool is_stage_cleared(const std::string& sid) const;
    Json stage_stars(const std::string& sid) const;
    int star_count(const std::string& sid) const;
    std::string player_name() const;
    int all_stars() const;
    int total_stars(const std::string& world_id) const;
    std::string next_stage_id(const std::string& sid) const;
    bool world_unlocked(const std::string& wid) const;
    bool tower_open(const std::string& tid) const;
    int tower_highest_floor(const std::string& tid) const;
    int stages_cleared_count() const;
    bool feature_unlocked(const std::string& f) const;
    std::string feature_unlock_label(const std::string& f) const;
    Json features_unlocked_by(const std::string& sid) const;

    // battles
    Json try_start_stage(const std::string& sid);        // {ok, reason}
    Json apply_battle_result(const std::string& sid, const Json& data);
    void record_defeat();

    // summoning
    Json summon_banner(const std::string& id = "standard") const;
    Json summon(const std::string& banner_id, int count);

    // missions & login
    std::string date_key() const;
    std::string week_key() const;
    void refresh_missions();
    void track(const std::string& event, int amount = 1, bool persist = true);
    int mission_progress(const std::string& kind, const Json& mission);
    bool mission_claimed(const std::string& kind, const std::string& id) const;
    Json claim_mission(const std::string& kind, const std::string& id);
    Json claim_all_missions();
    int daily_completed() const;
    bool can_claim_chest();
    Json claim_chest();
    int missions_claimable();
    bool login_available() const;
    int login_day_index() const;
    Json claim_login();

    // notifications & tutorial
    bool units_badge();
    bool summon_badge() const;
    void mark_summon_seen();
    bool hint_seen(const std::string& id) const;
    void mark_hint_seen(const std::string& id);
    bool coach_done(const std::string& id) const;
    void mark_coach_done(const std::string& id);
    void reset_tutorial();
    void mark_intro_seen();
    bool feature_announced(const std::string& f) const;
    void mark_feature_announced(const std::string& f);
    static std::string validate_player_name(std::string n);
    void set_player_name(std::string n);

    // settings
    void set_setting(const std::string& key, const Json& value);

private:
    Json grant_unlock_gift(const std::string& sid);
    void grant_retroactive_unlocks();
    Json add_rank_xp(int xp);
    int stage_sort_key(const std::string& sid) const;
    static void merge_reward(Json& total, const Json& r);
    double _play_accum = 0, _energy_tick = 0;
};

#define GM GameManager::get()
