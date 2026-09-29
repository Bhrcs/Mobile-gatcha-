// Help & Guide (scripts/ui/help.gd): short topics a player can look up at any time. Opened from MENU,
// from the "?" in screen headers (with a topic) and from the battle pause menu.
#include "screens/Screens.h"

using namespace gd;

namespace {
struct Entry { const char *icon, *heading, *text; };
}  // namespace
static const std::vector<std::string> TOPICS{"BASICS", "BATTLE", "ELEMENTS", "HEROES", "PROGRESS"};
static const std::map<std::string, std::vector<Entry>> PAGES{
    {"BASICS", {
        {"assets/icons/nav_quest.png", "Quest", "Pick a world, then a stage on its map. Stages cost Energy and give EXP, Gold, items and up to 3 stars."},
        {"assets/icons/energy.png", "Energy", "Energy refills over time, even while the game is closed, and fully on every Rank Up."},
        {"assets/icons/nav_units.png", "Units", "Your heroes. Train them with Wisps, evolve them at max level and pick your squad."},
        {"assets/icons/nav_summon.png", "Summon", "Spend Gems at the Embergate for new heroes. Duplicates become Soul Shards."},
        {"assets/icons/back.png", "Getting around", "BACK (top left) always returns to where you came from. On PC, Esc works as Back and Enter confirms."},
    }},
    {"BATTLE", {
        {"assets/icons/sword.png", "Attack", "Tap an enemy to target it, then tap a hero card to attack. Each hero acts once per turn."},
        {"assets/icons/burst.png", "Burst", "When a hero's Burst gauge is full, swipe UP on their card for their Burst skill. Attacking, guarding and taking hits fill it."},
        {"assets/icons/shield.png", "Guard", "Swipe DOWN on a card to Guard: half damage this turn and extra Burst gauge. Guard when an enemy shows WARNING."},
        {"assets/icons/auto.png", "Auto & speed", "AUTO lets heroes fight on their own (they Burst and Guard sensibly). 1x / 2x changes battle speed."},
        {"assets/icons/status_burn.png", "Status effects", "Icons under a unit show effects such as Burn, Poison, Shield or ATK Up. Tap or hover an icon to read it."},
        {"assets/icons/star.png", "Stars", "Each stage has three star goals (for example: clear it, no hero knocked out, clear within a number of turns)."},
    }},
    {"HEROES", {
        {"assets/icons/xp.png", "Training", "Feed Wisps and Gold to level a hero up. Wisps of the hero's own element give +50% EXP."},
        {"assets/icons/star.png", "Evolution", "At max level a hero can evolve into a stronger form. WHERE TO FIND shows where each material drops."},
        {"assets/icons/leader.png", "Leader", "Your leader's Leader Skill boosts the whole squad. Set the leader in SQUAD."},
        {"assets/icons/role_attacker.png", "Roles", "Attackers deal damage, Defenders protect, Healers restore HP, Supporters buff and Breakers weaken enemies."},
        {"assets/icons/soul_shard.png", "Soul Shards", "Duplicate summons turn into Soul Shards. Spend them on any hero to raise their Burst level."},
    }},
    {"PROGRESS", {
        {"assets/icons/rank.png", "Rank", "Battles give Rank EXP. Rank Ups refill Energy, raise Max Energy and sometimes give Gems."},
        {"assets/icons/tower.png", "Elemental Towers", "Ember, Tide and Verdant Towers are the best source of evolution materials. Each floor is harder."},
        {"assets/icons/missions.png", "Missions", "Daily and weekly missions give Gems, Gold and Wisps. Log in each day for the 7-day reward track."},
        {"assets/icons/lock.png", "Unlocks", "New features open as you clear World 1. A locked button always says which stage opens it."},
    }},
};

class HelpScreen : public ScreenBase
{
public:
    BoxContainer* body = nullptr;
    CinderTabs* tabs = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        back_fallback = "menu";
        auto area = build_frame("bg_camp", "HELP & GUIDE", "menu", nullptr, 0.6f);
        auto col = UIKit::vbox(UIKit::SP_L);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);
        std::string topic = upper(S(params(), "topic", "BASICS"));
        // header "?" topics map onto the guide pages
        static const std::map<std::string, std::string> ALIAS{{"SQUAD", "ELEMENTS"}, {"UNITS", "HEROES"}, {"SUMMON", "HEROES"}, {"TOWER", "PROGRESS"}};
        if (ALIAS.count(topic)) topic = ALIAS.at(topic);
        auto found = std::find(TOPICS.begin(), TOPICS.end(), topic);
        int start = found == TOPICS.end() ? 0 : (int)(found - TOPICS.begin());
        tabs = CinderTabs::make(TOPICS, start, [this](int i) { show(i); }, 88);
        col->add(tabs);
        auto scroll = ScrollContainer::create();
        scroll->set_v_flags(SIZE_EXPAND_FILL);
        col->add(scroll);
        body = UIKit::vbox(UIKit::SP_M);
        body->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(body);
        show(start);
    }

    void show(int i)
    {
        SceneRouter::remember({{"topic", TOPICS[i]}});
        body->clear_children();
        if (TOPICS[i] == "ELEMENTS")
        {
            auto p = PanelFrame::make("panel", 20);
            body->add(p);
            auto v = UIKit::vbox(UIKit::SP_M);
            p->add(v);
            auto chart = ElementChart::make();
            chart->set_h_flags(SIZE_SHRINK_CENTER);
            v->add(chart);
            for (auto& line : ElementChart::explanation())
            {
                auto l = UIKit::wrap_label(line, UIKit::T_BODY);
                l->h_align = ALIGN_CENTER;
                v->add(l);
            }
            body->add(entry({"assets/icons/info.png", "In battle",
                             "ADVANTAGE numbers mean a strong hit, RESIST numbers a weak one. The squad screen warns you when your team is weak against a stage."}));
            return;
        }
        auto it = PAGES.find(TOPICS[i]);
        if (it != PAGES.end())
            for (auto& e : it->second) body->add(entry(e));
    }

    static Control* entry(const Entry& e)
    {
        auto p = PanelFrame::make("inset", 16);
        auto h = UIKit::hbox(UIKit::SP_L);
        p->add(h);
        auto ic = UIKit::icon(e.icon, 64);
        ic->set_v_flags(SIZE_SHRINK_BEGIN);
        h->add(ic);
        auto v = UIKit::vbox(UIKit::SP_XS);
        v->set_h_flags(SIZE_EXPAND_FILL);
        v->add(UIKit::label(e.heading, UIKit::T_NAME, UIKit::GOLD, ALIGN_LEFT, 8));
        v->add(UIKit::wrap_label(e.text, UIKit::T_BODY));
        h->add(v);
        return p;
    }
};
REGISTER_SCREEN("help", HelpScreen)
