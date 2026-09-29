// Unit collection (scripts/ui/units.gd): rarity-framed cards, quick element chips and
// the FILTER & SORT overlay. The choice is remembered between sessions.
#include "screens/Screens.h"

using namespace UIKit;

class UnitsScreen : public ScreenBase
{
public:
    gd::GridContainer* grid = nullptr;
    gd::Label* count_label = nullptr;
    FantasyButton* sort_button = nullptr;
    FantasyButton* filter_button = nullptr;
    Json state;
    std::map<std::string, gd::Button*> chips;

    void ready() override
    {
        if (!require_profile()) return;
        state = UnitFilter::load_state();
        auto area = build_frame("bg_camp", "UNITS", "units", nullptr, 0.55f, true, {{"help", "units"}});
        auto col = vbox(12);
        col->set_anchors_preset(gd::PRESET_FULL_RECT);
        area->add(col);

        // filter + sort bar
        auto bar = PanelFrame::make("plank", 10);
        col->add(bar);
        auto row = hbox(8);
        bar->add(row);
        for (std::string el : {"all", "fire", "water", "nature"})
        {
            auto chip = gd::Button::create();
            chip->set_name("Filter_" + el);
            chip->set_custom_min(Vec2(96, 96));
            if (el == "all")
            {
                chip->set_text("ALL");
                chip->set_font_size(30);
            }
            else
            {
                chip->set_icon("assets/icons/orb_" + el + ".png");
                chip->icon_max_width = 84;   // expand_icon: fill the chip's content height
            }
            chip->tooltip_text = "Show " + (el == "all" ? std::string("all") : DB.element_name(el)) + " units";
            hook_sounds(chip);
            chip->pressed.connect([this, el] { set_filter(el); });
            row->add(chip);
            chips[el] = chip;
        }
        row->add(spacer());
        auto codex = btn("", "secondary", Vec2(96, 96), "assets/icons/codex.png");
        codex->set_name("CodexButton");
        codex->tooltip_text = "Codex";
        codex->pressed.connect([] { SceneRouter::go("codex"); });
        row->add(codex);
        filter_button = btn("FILTER", "secondary", Vec2(190, 96), "assets/icons/filter.png");
        filter_button->set_name("FilterButton");
        filter_button->set_font_size(T_SMALL);
        filter_button->pressed.connect([this] { open_filter(); });
        row->add(filter_button);
        sort_button = btn("", "secondary", Vec2(210, 96), "assets/icons/sort.png");
        sort_button->set_name("SortButton");
        sort_button->set_font_size(T_SMALL);
        sort_button->pressed.connect([this] { open_filter(); });
        row->add(sort_button);

        auto info = hbox(12);
        auto hint = label("Tap a hero to train, evolve or inspect.", T_SMALL, MUTED);
        hint->set_h_flags(gd::SIZE_EXPAND_FILL);
        info->add(hint);
        count_label = label("", T_BODY, GOLD, gd::ALIGN_RIGHT, 6);
        info->add(count_label);
        col->add(info);

        auto scroll = gd::ScrollContainer::create();
        scroll->set_v_flags(gd::SIZE_EXPAND_FILL);
        col->add(scroll);
        auto center = gd::CenterContainer::create();
        center->set_h_flags(gd::SIZE_EXPAND_FILL);
        scroll->add(center);
        grid = gd::GridContainer::create(4);
        grid->h_separation = 12;
        grid->v_separation = 14;
        center->add(grid);
        AudioManager::play_music("menu");
        rebuild();
    }

    void set_filter(const std::string& el)
    {
        state["el"] = el;
        UnitFilter::save_state(state);
        rebuild();
    }

    void open_filter()
    {
        UnitFilter::open(this, state, [this](Json st) {
            state = st;
            rebuild();
        });
    }

    void rebuild()
    {
        sort_button->set_text(UnitFilter::sort_label(state));
        int active = UnitFilter::active_count(state);
        filter_button->set_text(active == 0 ? "FILTER" : UIKit::fmt("FILTER %d", active));
        filter_button->set_selected(active > 0);
        for (auto& [el, chip] : chips)
        {
            bool on = el == S(state, "el");
            auto sb = tex_style(on ? "v2_chip_on.png" : "v2_chip.png", 9, 6);
            for (auto s : {gd::Button::NORMAL, gd::Button::HOVER, gd::Button::PRESSED}) chip->set_style(s, sb);
            chip->set_modulate(on ? Col::WHITE : Col(0.75f, 0.74f, 0.8f));
        }
        grid->clear_children();
        std::vector<Json> units;
        Json owned = GM.units();
        for (size_t i = 0; i < owned.size(); i++)
        {
            const Json& u = owned[i];
            const Json& def = DB.character(S(u, "char_id"));
            if (!UnitFilter::matches(state, u, def)) continue;
            units.push_back({{"unit", u}, {"def", def}, {"idx", i}, {"stats", GM.unit_stats(u)}});
        }
        std::sort(units.begin(), units.end(), [this](const Json& a, const Json& b) { return UnitFilter::compare(state, a, b); });
        for (auto& entry : units)
        {
            auto card = UnitCard::make(entry["unit"]);
            card->tapped.connect([](std::string uid) {
                AudioManager::play_sfx("unit_select", 0.03f);
                SceneRouter::go("unit_detail", {{"uid", uid}});
            });
            grid->add(card);
        }
        count_label->set_text(UIKit::fmt("UNITS  %d / %d    CODEX %d / %d", (int)units.size(), (int)owned.size(),
                                  (int)A(GM.profile, "codex").size(), (int)DB.family_ids().size()));
        if (units.empty())
        {
            // empty state: say why and how to get out of it
            auto box = vbox(SP_M);
            box->set_custom_min(Vec2(1000, 260));
            box->alignment = gd::ALIGNMENT_CENTER;
            box->add(label("No heroes match these filters.", T_BODY, MUTED, gd::ALIGN_CENTER));
            auto clear = btn("CLEAR FILTERS", "secondary", Vec2(360, 100));
            clear->set_name("ClearFilters");
            clear->set_h_flags(gd::SIZE_SHRINK_CENTER);
            clear->pressed.connect([this] {
                state["el"] = "all";
                state["rarity"] = 0;
                state["role"] = "";
                state["evolve"] = false;
                state["fav"] = false;
                UnitFilter::save_state(state);
                rebuild();
            });
            box->add(clear);
            grid->add(box);
        }
    }
};
REGISTER_SCREEN("units", UnitsScreen)
