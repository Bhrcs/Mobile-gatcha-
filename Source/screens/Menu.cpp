// MENU tab (scripts/ui/menu.gd): everything that is not a main tab, as large labelled tiles.
// Locked features stay visible, dimmed with a lock, and say where they open.
#include "screens/Screens.h"

using namespace gd;

namespace {
struct MenuItem { const char *label, *icon, *scene, *feature, *desc; };
}  // namespace
static const MenuItem ITEMS[] = {
    {"SQUAD", "assets/icons/leader.png", "squad", "squad", "Choose who fights and who leads"},
    {"ITEMS", "assets/icons/nav_bag.png", "inventory", "", "Materials, wisps and treasures"},
    {"MISSIONS", "assets/icons/missions.png", "missions", "missions", "Daily & weekly goals, login bonus"},
    {"TOWERS", "assets/icons/tower.png", "tower", "tower", "Evolution materials"},
    {"CODEX", "assets/icons/codex.png", "codex", "units", "Every hero you have met"},
    {"PROFILE", "assets/icons/profile.png", "profile", "", "Rank, records and your name"},
    {"SETTINGS", "assets/icons/nav_settings.png", "settings", "", "Audio, gameplay, graphics"},
    {"HELP", "assets/icons/help.png", "help", "", "Guide, elements and tips"},
};

class MenuScreen : public ScreenBase
{
public:
    void ready() override
    {
        if (!require_profile()) return;
        auto area = build_frame("bg_camp", "MENU", "menu", nullptr, 0.6f);
        auto scroll = ScrollContainer::create();
        scroll->set_anchors_preset(PRESET_FULL_RECT);
        area->add(scroll);
        auto v = UIKit::vbox(UIKit::SP_L);
        v->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(v);
        auto grid = GridContainer::create(2);
        grid->set_name("MenuGrid");
        grid->set_h_flags(SIZE_EXPAND_FILL);
        grid->h_separation = UIKit::SP_M;
        grid->v_separation = UIKit::SP_M;
        v->add(grid);
        for (auto& it : ITEMS) grid->add(tile(it));
        auto title = UIKit::btn("TITLE SCREEN", "quiet", Vec2(420, 100));
        title->set_name("Menu_TITLE");
        title->set_h_flags(SIZE_SHRINK_CENTER);
        title->pressed.connect([] { SceneRouter::go("main_menu"); });
        v->add(title);
        v->add(UIKit::label("Cinderbound v0.6.0", UIKit::T_SMALL, UIKit::MUTED, ALIGN_CENTER));
    }

    static Control* tile(const MenuItem& it)
    {
        auto b = UIKit::btn("", "secondary", Vec2(0, 170));
        b->set_name(std::string("Menu_") + it.label);
        b->set_h_flags(SIZE_EXPAND_FILL);
        auto h = UIKit::hbox(UIKit::SP_M);
        h->set_mouse_filter(MOUSE_IGNORE);
        h->set_anchors_preset(PRESET_FULL_RECT);
        h->set_offsets(26, 8, -16, -14);
        b->add(h);
        h->add(UIKit::icon(it.icon, 80));
        auto col = UIKit::vbox(2);
        col->set_mouse_filter(MOUSE_IGNORE);
        col->alignment = ALIGNMENT_CENTER;
        col->set_h_flags(SIZE_EXPAND_FILL);
        col->add(UIKit::label(it.label, UIKit::T_NAME, Col::WHITE, ALIGN_LEFT, 10));
        auto d = UIKit::label(it.desc, UIKit::T_SMALL, Col("#d8d0e0"), ALIGN_LEFT, 5);
        d->set_autowrap(true);
        col->add(d);
        h->add(col);
        std::string scene = it.scene, feature = it.feature;
        if (!feature.empty() && !GM.feature_unlocked(feature))
        {
            b->set_modulate(Col(0.55f, 0.53f, 0.58f));
            auto lk = UIKit::icon("assets/icons/lock.png", 40);
            lk->set_position(Vec2(12, 12));
            b->add(lk);
            d->set_text("Opens after " + GM.feature_unlock_label(feature));
            std::string name = it.label;
            std::transform(name.begin() + 1, name.end(), name.begin() + 1, ::tolower);   // String.capitalize()
            b->pressed.connect([name, feature] {
                UIManager::toast(name + " unlocks after clearing " + GM.feature_unlock_label(feature) + ".", "info");
            });
        }
        else
        {
            b->pressed.connect([scene] { SceneRouter::go(scene); });
            if (scene == "missions")
            {
                int mc = GM.missions_claimable();
                if (mc > 0) UIKit::badge(b, std::to_string(mc));
                else if (GM.login_available()) UIKit::badge(b);
            }
        }
        return b;
    }
};
REGISTER_SCREEN("menu", MenuScreen)
