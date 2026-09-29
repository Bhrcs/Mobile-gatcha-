#pragma once
// Everything a screen needs, plus the shared components used across screens.
// Each component is implemented in exactly one .cpp (owner noted); signatures
// mirror the Godot originals in scripts/ui/components/.
#include "ui/UIKit.h"
#include "ui/Sprites.h"
#include "logic/Battle.h"

// ---- components/Widgets.cpp -------------------------------------------------
class CinderTabs : public gd::BoxContainer   // cinder_tabs.gd
{
public:
    static CinderTabs* make(const std::vector<std::string>& labels, int current = 0,
                            std::function<void(int)> on_change = nullptr, int height = 96);
    void select(int i, bool emit = true);
    void set_badge(int i, const std::string& text = "!");
    Signal<int> tab_changed;
    int selected = 0;
    std::vector<std::string> labels;
    std::vector<FantasyButton*> tabs;
};

class CinderSwitch : public gd::BaseButton   // cinder_switch.gd
{
public:
    static CinderSwitch* make(bool start_on, std::function<void(bool)> on_toggle = nullptr);
    void set_on(bool v);
    bool on = false;
    Signal<bool> toggled_to;
};

namespace ElementChart   // element_chart.gd
{
gd::Control* make();
FantasyPopup* popup(gd::Control* parent);
std::vector<std::string> explanation();
}  // namespace ElementChart

namespace SettingsPanel   // settings_panel.gd
{
FantasyPopup* open(gd::Control* parent, int category = 0);
void fill(gd::BoxContainer* v, const std::string& category, gd::Control* host);
}  // namespace SettingsPanel

// ---- components/Rewards.cpp -------------------------------------------------
class RewardItem : public gd::Control   // reward_item.gd
{
public:
    static constexpr int SIZE = 150;
    static RewardItem* make(const std::string& icon_path, const std::string& qty, const std::string& caption = "", int slot_px = SIZE);
    void pop(float delay, bool silent = false);
    bool hidden_start = true;
    std::string icon_path, qty_text, caption;
    int px = SIZE;
};

namespace RewardPopup   // reward_popup.gd
{
FantasyPopup* open(gd::Control* parent, const std::string& title, const Json& r, const std::string& sub = "");
}

namespace EnergyPopup   // energy_popup.gd
{
FantasyPopup* open(gd::Control* parent, const std::string& stage_id);
}

class StageNode : public gd::Control   // stage_node.gd
{
public:
    static StageNode* make(const std::string& sid, const std::string& state, int px);
    void set_selected(bool on);
    std::string stage_id, state = "locked";
};

namespace StageInfo   // stage_info.gd
{
Json species(const Json& stage);
Json elements(const Json& stage);
Json possible_drops(const Json& stage);
gd::Control* chip(const std::string& label_text, const std::string& value, const Col& color = UIKit::TEXT, const std::string& icon_path = "");
gd::Control* info_row(const Json& stage);
gd::Control* stars_row(const Json& stage);
gd::Control* rewards_row(const Json& stage, int px = 88);
gd::Control* matchup_row(const Json& party, const Json& stage, gd::Control* host);
std::vector<std::string> matchup_advice(const Json& mine, const Json& foes);
FantasyPopup* open_prepare(gd::Control* parent, const std::string& stage_id, const std::string& back_scene = "stage_select");
}  // namespace StageInfo

class RankUpOverlay : public gd::Control   // rank_up_overlay.gd
{
public:
    static RankUpOverlay* play(gd::Control* parent, const Json& ups);
    Signal<> closed;
};

// ---- components/UnitWidgets.cpp ----------------------------------------------
class UnitCard : public gd::Control   // unit_card.gd
{
public:
    static UnitCard* make(const Json& u);
    static gd::TextureRect* role_icon(const Json& def, int size = 32);
    void set_selected(bool on);
    Signal<std::string> tapped;
    Json unit = Json::object();
    bool selected = false;
};

namespace UnitFilter   // unit_filter.gd
{
Json load_state();
void save_state(const Json& st);
int active_count(const Json& st);
std::string sort_label(const Json& st);
bool matches(const Json& st, const Json& u, const Json& def);
bool compare(const Json& st, const Json& a, const Json& b);
FantasyPopup* open(gd::Control* parent, const Json& st, std::function<void(Json)> on_apply);
}  // namespace UnitFilter

namespace SkillText   // skill_text.gd
{
std::vector<std::pair<std::string, Col>> tags(const Json& sk);
gd::FlowContainer* chips(const Json& sk, const Col& accent = UIKit::SKY);
}  // namespace SkillText

class StatRow : public gd::BoxContainer   // stat_row.gd
{
public:
    static StatRow* make(const std::string& stat_name, int value, int ref_max, const Col& color = UIKit::SKY);
};

class StatusIcon : public gd::Control   // status_icon.gd
{
public:
    static StatusIcon* make(const std::string& sid, int turns, float value = 0, int px = 32);
    std::string describe() const;
    std::string status_id;
    int turns = 0;
    float value = 0;
};

namespace ItemSources   // item_sources.gd
{
FantasyPopup* open(gd::Control* parent, const std::string& item_id);
}
