#pragma once
// Local, offline JSON saves with atomic writes (.tmp then rename), a rolling .bak
// used automatically when the main file is unreadable, and field-by-field repair
// of missing / wrong-typed data. Settings live in their own file.
#include "Json.h"

class SaveManager
{
public:
    static SaveManager& get();
    static constexpr int SAVE_VERSION = 2;
    std::string save_path, settings_path;   // default: <writable>/cinderbound_save.json
    std::string last_load_status = "missing";  // ok | missing | recovered_backup | corrupted
    std::vector<std::string> migration_notes;

    Json default_profile() const;
    Json default_settings() const;
    bool has_save() const;
    Json load_profile();                     // {} when no usable save exists
    bool save_profile(const Json& profile);
    void delete_profile();
    Json load_settings();
    void save_settings(const Json& s);
    Json sanitize_profile(const Json& data, bool record_notes = true);
    int max_energy_for_rank(int rank) const;

private:
    SaveManager();
    Json read_dict(const std::string& path) const;
    bool write_atomic(const std::string& path, const std::string& text) const;
};
