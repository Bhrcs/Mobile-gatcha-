// Missions (scripts/ui/missions.gd): 5 daily missions with a daily chest (claim 4), weekly missions and
// the 7-day login calendar. Progress resets at local midnight / on Mondays.
#include "screens/Screens.h"
#include <ctime>

using namespace gd;

static const std::vector<std::string> TABS{"daily", "weekly", "login"};

static std::string reward_text(const Json& r)
{
    std::string s;
    auto part = [&s](const std::string& p) { s += (s.empty() ? "" : "\n") + p; };
    if (I(r, "gems", 0) > 0) part(UIKit::fmt("%d Gems", I(r, "gems", 0)));
    if (I(r, "gold", 0) > 0) part(UIKit::format_number(I(r, "gold", 0)) + " Gold");
    for (auto& [id, q] : O(r, "items").items()) part(UIKit::fmt("%s x%d", DB.item_name(id).c_str(), I(q)));
    return s;
}

class MissionsScreen : public ScreenBase
{
public:
    BoxContainer* body = nullptr;
    std::string tab = "daily";
    CinderTabs* tabs = nullptr;
    FantasyButton* claim_all = nullptr;
    Label* reset_l = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        auto area = build_frame("bg_camp", "MISSIONS", "missions", nullptr, 0.6f);
        if (!GM.feature_unlocked("missions"))
        {
            auto lock = UIKit::wrap_label("Missions unlock after clearing " + GM.feature_unlock_label("missions") + ".", UIKit::T_NAME, UIKit::MUTED);
            lock->h_align = ALIGN_CENTER;
            lock->set_anchors_preset(PRESET_CENTER);
            lock->set_min_w(900);
            area->add(lock);
            return;
        }
        auto col = UIKit::vbox(12);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);
        tabs = CinderTabs::make({"DAILY", "WEEKLY", "LOGIN"}, 0, [this](int i) { set_tab(TABS[i]); });
        col->add(tabs);
        auto top = UIKit::hbox(UIKit::SP_M);
        reset_l = UIKit::label("", UIKit::T_SMALL, UIKit::MUTED, ALIGN_LEFT, 4);
        reset_l->set_h_flags(SIZE_EXPAND_FILL);
        top->add(reset_l);
        claim_all = UIKit::btn("CLAIM ALL", "reward", Vec2(300, 90));
        claim_all->set_name("ClaimAll");
        claim_all->pressed.connect([this] { do_claim_all(); });
        top->add(claim_all);
        col->add(top);
        auto scroll = ScrollContainer::create();
        scroll->set_v_flags(SIZE_EXPAND_FILL);
        col->add(scroll);
        body = UIKit::vbox(10);
        body->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(body);
        std::string start = S(params(), "tab", "daily");
        set_tab(std::find(TABS.begin(), TABS.end(), start) != TABS.end() ? start : "daily");
    }

    static int tab_index(const std::string& t) { return (int)(std::find(TABS.begin(), TABS.end(), t) - TABS.begin()); }

    void set_tab(const std::string& t)
    {
        tab = t;
        SceneRouter::remember({{"tab", t}});
        tabs->select(tab_index(t), false);
        int total = 0;
        for (std::string k : {"daily", "weekly"})
        {
            int n = 0;
            for (auto& m : A(DB.missions, k))
                if (!GM.mission_claimed(k, S(m, "id")) && GM.mission_progress(k, m) >= I(m, "target", 1)) ++n;
            if (k == "daily" && GM.can_claim_chest()) ++n;
            tabs->set_badge(tab_index(k), n > 0 ? std::to_string(n) : "");
            total += n;
        }
        tabs->set_badge(2, GM.login_available() ? "!" : "");
        claim_all->setVisible(total > 0 && t != "login");
        claim_all->set_text(UIKit::fmt("CLAIM ALL (%d)", total));
        render();
    }

    void do_claim_all()
    {
        Json r = GM.claim_all_missions();
        if (I(r, "count", 0) <= 0)
        {
            UIManager::toast("Nothing to claim yet.", "info");
            return;
        }
        UIManager::sfx("claim");
        UIManager::haptic("confirm");
        RewardPopup::open(this, UIKit::fmt("%d REWARDS CLAIMED", I(r, "count", 0)), r);
        set_tab(tab);
    }

    void render()
    {
        body->clear_children();
        update_reset_label();
        if (tab == "daily")
        {
            body->add(chest());
            for (auto& m : A(DB.missions, "daily")) body->add(mission_row("daily", m));
        }
        else if (tab == "weekly")
            for (auto& m : A(DB.missions, "weekly")) body->add(mission_row("weekly", m));
        else if (tab == "login")
            login_calendar();
    }

    void update_reset_label()
    {
        std::time_t now_t = std::time(nullptr);
        std::tm dt = *std::localtime(&now_t);
        int secs_to_midnight = 86400 - (dt.tm_hour * 3600 + dt.tm_min * 60 + dt.tm_sec);
        if (tab == "weekly")
        {
            int days = (8 - dt.tm_wday) % 7;   // tm_wday: 0 = Sunday
            if (days == 0) days = 7;
            reset_l->set_text(UIKit::fmt("Weekly missions reset in %dd ", days - 1) + UIKit::format_time(secs_to_midnight));
        }
        else
            reset_l->set_text("Daily missions reset in " + UIKit::format_time(secs_to_midnight));
        if (GM.now() < 0) reset_l->set_text("");
    }

    Control* chest()
    {
        const Json& info = O(DB.missions, "daily_chest");
        int need = I(info, "needed", 4);
        int done = GM.daily_completed();
        auto p = PanelFrame::make(GM.can_claim_chest() ? "boss" : "panel", 16);
        p->set_name("DailyChest");
        auto h = UIKit::hbox(14);
        p->add(h);
        bool claimed = B(O(GM.profile, "missions"), "chest_claimed", false);
        h->add(UIKit::icon(claimed ? "assets/icons/chest_open.png" : "assets/icons/chest.png", 96));
        auto v = UIKit::vbox(4);
        v->set_h_flags(SIZE_EXPAND_FILL);
        v->add(UIKit::label("DAILY CHEST", UIKit::T_NAME, UIKit::GOLD, ALIGN_LEFT, 8));
        v->add(UIKit::label(UIKit::fmt("Claim %d daily missions: %d / %d", need, std::min(done, need), need), UIKit::T_BODY, UIKit::TEXT, ALIGN_LEFT, 6));
        v->add(reward_line(O(info, "reward")));
        h->add(v);
        auto b = FantasyButton::make(claimed ? "CLAIMED" : "CLAIM", "gold", Vec2(220, 100));
        b->set_name("ClaimChest");
        b->set_disabled(!GM.can_claim_chest());
        b->pressed.connect([this] {
            Json r = GM.claim_chest();
            if (!r.empty())
            {
                AudioManager::play_sfx("claim");
                reward_popup(r);
            }
            set_tab(tab);
        });
        h->add(b);
        return p;
    }

    Control* mission_row(const std::string& kind, const Json& m)
    {
        int prog = GM.mission_progress(kind, m);
        int target = I(m, "target", 1);
        std::string id = S(m, "id");
        bool claimed = GM.mission_claimed(kind, id);
        bool done = prog >= target;
        auto p = PanelFrame::make(!claimed ? "plank" : "inset", 12);
        p->set_name("Mission_" + id);
        auto h = UIKit::hbox(12);
        p->add(h);
        auto v = UIKit::vbox(4);
        v->set_h_flags(SIZE_EXPAND_FILL);
        v->add(UIKit::label(S(m, "text"), UIKit::T_BODY, !claimed ? UIKit::TEXT : UIKit::MUTED, ALIGN_LEFT, 6));
        auto pr = UIKit::hbox(10);
        auto bar = ResourceBar::make("xp", 22);
        bar->set_h_flags(SIZE_EXPAND_FILL);
        bar->set_v_flags(SIZE_SHRINK_CENTER);
        bar->set_values((float)prog, (float)target, false);
        pr->add(bar);
        pr->add(UIKit::label(UIKit::fmt("%d / %d", prog, target), UIKit::T_SMALL, UIKit::GOLD, ALIGN_RIGHT, 5));
        v->add(pr);
        v->add(reward_line(O(m, "reward")));
        h->add(v);
        auto b = FantasyButton::make(claimed ? "DONE" : (done ? "CLAIM" : "GO"), done && !claimed ? "gold" : "stone", Vec2(200, 96));
        b->set_name("Claim_" + id);
        b->set_font_size(30);
        if (claimed)
            b->set_disabled(true);
        else if (done)
            b->pressed.connect([this, kind, id] {
                Json r = GM.claim_mission(kind, id);
                if (!r.empty())
                {
                    AudioManager::play_sfx("claim");
                    reward_popup(r);
                }
                set_tab(tab);
            });
        else
        {
            std::string ev = S(m, "event");
            b->pressed.connect([ev] { go_for(ev); });
        }
        h->add(b);
        return p;
    }

    static void go_for(const std::string& ev)
    {
        if (ev == "tower_clear") SceneRouter::go("tower");
        else if (ev == "train") SceneRouter::go("units");
        else if (ev == "summon") SceneRouter::go("summon");
        else SceneRouter::go("stage_select");
    }

    static Control* reward_line(const Json& r)
    {
        auto h = UIKit::hbox(8);
        h->add(UIKit::label("REWARD", UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 5));
        if (I(r, "gems", 0) > 0)
        {
            h->add(UIKit::icon("assets/icons/gem.png", 36));
            h->add(UIKit::label(std::to_string(I(r, "gems", 0)), UIKit::T_SMALL, Col("#9ae8ff"), ALIGN_LEFT, 5));
        }
        if (I(r, "gold", 0) > 0)
        {
            h->add(UIKit::icon("assets/icons/gold.png", 36));
            h->add(UIKit::label(UIKit::format_number(I(r, "gold", 0)), UIKit::T_SMALL, UIKit::GOLD, ALIGN_LEFT, 5));
        }
        for (auto& [id, q] : O(r, "items").items())
        {
            h->add(UIKit::icon(res(S(DB.item(id), "icon")), 36));
            h->add(UIKit::label(UIKit::fmt("x%d", I(q)), UIKit::T_SMALL, UIKit::TEXT, ALIGN_LEFT, 5));
        }
        return h;
    }

    void login_calendar()
    {
        const Json& cycle = A(DB.login_rewards, "cycle");
        int today = GM.login_day_index();
        bool avail = GM.login_available();
        auto info = UIKit::wrap_label("Log in on any day to claim the next reward. Missed days never reset the calendar.", UIKit::T_SMALL, UIKit::MUTED);
        info->set_min_w(1000);
        info->h_align = ALIGN_CENTER;
        body->add(info);
        auto grid = GridContainer::create(4);
        grid->h_separation = 10;
        grid->v_separation = 10;
        grid->set_h_flags(SIZE_SHRINK_CENTER);
        body->add(grid);
        int claimed_count = I(O(GM.profile, "login"), "day_index", 0) % std::max((int)cycle.size(), 1);
        for (int i = 0; i < (int)cycle.size(); ++i)
        {
            bool is_next = i == today;
            bool done = i < claimed_count;
            auto cell = PanelFrame::make(is_next && avail ? "boss" : (done ? "inset" : "panel"), 10);
            cell->set_name(UIKit::fmt("LoginDay_%d", i + 1));
            cell->set_custom_min(Vec2(240, 230));
            auto v = UIKit::vbox(4);
            v->set_mouse_filter(MOUSE_IGNORE);
            cell->add(v);
            v->add(UIKit::label(UIKit::fmt("DAY %d", i + 1), UIKit::T_BODY, is_next ? UIKit::GOLD : UIKit::TEXT, ALIGN_CENTER, 6));
            const Json& r = O(cycle[i], "reward");
            std::string icon_path = "assets/icons/chest.png";
            if (I(r, "gems", 0) > 0) icon_path = "assets/icons/gem.png";
            else if (I(r, "gold", 0) > 0) icon_path = "assets/icons/gold.png";
            else if (!O(r, "items").empty()) icon_path = res(S(DB.item(O(r, "items").begin().key()), "icon", icon_path));
            auto ic = UIKit::icon(icon_path, 80);
            ic->set_h_flags(SIZE_SHRINK_CENTER);
            v->add(ic);
            v->add(UIKit::label(reward_text(r), UIKit::T_SMALL, UIKit::TEXT, ALIGN_CENTER, 5));
            if (done)
            {
                auto ch = UIKit::hbox(4);
                ch->alignment = ALIGNMENT_CENTER;
                ch->set_mouse_filter(MOUSE_IGNORE);
                ch->add(UIKit::icon("assets/icons/check.png", 32));
                ch->add(UIKit::label("CLAIMED", UIKit::T_SMALL, UIKit::GOOD, ALIGN_CENTER, 5));
                v->add(ch);
                ic->set_modulate(Col(0.6f, 0.6f, 0.65f));
            }
            else if (is_next && avail)
                v->add(UIKit::label("TODAY", UIKit::T_SMALL, UIKit::GOLD, ALIGN_CENTER, 5));
            grid->add(cell);
        }
        auto b = FantasyButton::make(avail ? UIKit::fmt("CLAIM DAY %d", today + 1) : "COME BACK TOMORROW", avail ? "gold" : "stone", Vec2(560, 120));
        b->set_name("ClaimLogin");
        b->set_h_flags(SIZE_SHRINK_CENTER);
        b->set_disabled(!avail);
        b->pressed.connect([this] {
            Json r = GM.claim_login();
            if (!r.empty())
            {
                AudioManager::play_sfx("claim");
                reward_popup(r);
            }
            set_tab("login");
        });
        body->add(b);
    }

    void reward_popup(const Json& r) { RewardPopup::open(this, "REWARD CLAIMED", r); }
};
REGISTER_SCREEN("missions", MissionsScreen)
