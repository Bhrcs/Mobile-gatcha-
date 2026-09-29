// Settings screen (scripts/ui/settings.gd): AUDIO / GAMEPLAY / GRAPHICS / ACCOUNT tabs.
// The rows live in SettingsPanel so the title screen and battle pause menu show the same options.
#include "screens/Screens.h"

using namespace gd;

// SettingsPanel._categories(): the account page only exists once a journey does
static std::vector<std::string> categories()
{
    std::vector<std::string> c{"AUDIO", "GAMEPLAY", "GRAPHICS", "ACCOUNT"};
    if (!GM.has_profile()) c.pop_back();
    return c;
}

class SettingsScreen : public ScreenBase
{
public:
    BoxContainer* body = nullptr;
    CinderTabs* tabs = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        back_fallback = "menu";
        auto area = build_frame("bg_camp", "SETTINGS", "menu", nullptr, 0.6f);
        auto col = UIKit::vbox(UIKit::SP_L);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);
        auto cats = categories();
        int start = std::clamp(I(params(), "tab", 0), 0, (int)cats.size() - 1);
        tabs = CinderTabs::make(cats, start, [this](int i) { on_tab(i); });
        col->add(tabs);
        auto scroll = ScrollContainer::create();
        scroll->set_v_flags(SIZE_EXPAND_FILL);
        col->add(scroll);
        body = UIKit::vbox(UIKit::SP_M);
        body->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(body);
        SettingsPanel::fill(body, cats[start], this);
    }

    void on_tab(int i)
    {
        SceneRouter::remember({{"tab", i}});
        SettingsPanel::fill(body, categories()[i], this);
    }
};
REGISTER_SCREEN("settings", SettingsScreen)
