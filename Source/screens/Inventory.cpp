// Inventory (scripts/ui/inventory.gd): tabs MATERIALS / TRAINING / ITEMS / OTHER. Items stack in a grid of
// slots; the docked detail panel shows the selected item with WHERE TO FIND, and USE where it makes sense.
// OTHER lists the currencies: Gems, Gold, Soul Shards and Energy.
#include "screens/Screens.h"

using namespace gd;

static const std::vector<std::pair<std::string, std::string>> TABS{
    {"MATERIALS", "material"}, {"TRAINING", "training"}, {"ITEMS", "item"}, {"OTHER", "other"}};

class InventoryScreen : public ScreenBase
{
public:
    static constexpr int DETAIL_H = 360;
    BoxContainer* list = nullptr;
    GridContainer* grid = nullptr;
    BoxContainer* detail = nullptr;
    PanelFrame* detail_panel = nullptr;
    std::string category, selected;
    CinderTabs* tabs = nullptr;

    void ready() override
    {
        if (!require_profile()) return;
        back_fallback = "menu";
        auto area = build_frame("bg_camp", "ITEMS", "inventory", nullptr, 0.6f);
        auto col = UIKit::vbox(UIKit::SP_M);
        col->set_anchors_preset(PRESET_FULL_RECT);
        area->add(col);
        std::vector<std::string> labels;
        std::string start = S(params(), "tab", "material");
        int idx = 0;
        for (int i = 0; i < (int)TABS.size(); ++i)
        {
            labels.push_back(TABS[i].first);
            if (TABS[i].second == start) idx = i;
        }
        tabs = CinderTabs::make(labels, idx, [this](int i) { set_category(TABS[i].second); });
        col->add(tabs);
        auto scroll = ScrollContainer::create();
        scroll->set_v_flags(SIZE_EXPAND_FILL);
        col->add(scroll);
        list = UIKit::vbox(UIKit::SP_M);
        list->set_h_flags(SIZE_EXPAND_FILL);
        scroll->add(list);
        detail_panel = PanelFrame::make("panel", 18);
        detail_panel->set_name("ItemDetail");
        detail_panel->set_min_h(DETAIL_H);
        col->add(detail_panel);
        detail = UIKit::vbox(UIKit::SP_S);
        detail_panel->add(detail);
        set_category(TABS[idx].second);
    }

    void set_category(const std::string& cat)
    {
        category = cat;
        SceneRouter::remember({{"tab", cat}});
        list->clear_children();
        grid = nullptr;
        detail_panel->setVisible(cat != "other");
        if (cat == "other")
        {
            currencies();
            return;
        }
        const Json& inv = O(GM.profile, "inventory");
        std::vector<std::string> ids;
        for (auto& [k, q] : inv.items())
            if (I(q) > 0 && S(DB.item(k), "category") == cat) ids.push_back(k);
        std::sort(ids.begin(), ids.end(), [](const std::string& a, const std::string& b) {
            return I(DB.item(a), "sort", 99) < I(DB.item(b), "sort", 99);
        });
        if (ids.empty())
        {
            static const std::map<std::string, std::string> EMPTY{
                {"material", "No materials yet. Tower floors and later stages drop evolution materials."},
                {"training", "No wisps yet. Wisps drop from stages, bosses, towers, missions and login rewards."},
                {"item", "No items yet. Herbs and treasures drop from stages."}};
            auto p = PanelFrame::make("inset", 30);
            auto it = EMPTY.find(cat);
            auto empty = UIKit::wrap_label(it != EMPTY.end() ? it->second : "Nothing here yet.", UIKit::T_BODY, UIKit::MUTED);
            empty->h_align = ALIGN_CENTER;
            p->add(empty);
            list->add(p);
            selected = "";
            show_detail("");
            return;
        }
        grid = GridContainer::create(5);
        grid->h_separation = UIKit::SP_M;
        grid->v_separation = UIKit::SP_M;
        grid->set_h_flags(SIZE_SHRINK_CENTER);
        list->add(grid);
        for (auto& id : ids) grid->add(slot(id, I(inv, id, 0)));
        if (std::find(ids.begin(), ids.end(), selected) == ids.end()) selected = ids[0];
        show_detail(selected);
    }

    Control* slot(const std::string& item_id, int qty)
    {
        const Json& item = DB.item(item_id);
        auto cell = PanelFrame::make(item_id == selected ? "boss" : "slot", 10);
        cell->set_name("Item_" + item_id);
        cell->set_custom_min(Vec2(186, 186));
        auto holder = Control::create();
        holder->set_mouse_filter(MOUSE_IGNORE);
        cell->add(holder);
        auto ic = UIKit::icon(res(S(item, "icon")), 112);
        ic->set_position(Vec2(26, 10));
        holder->add(ic);
        auto q = UIKit::label("x" + UIKit::format_compact(qty), UIKit::T_BODY, Col::WHITE, ALIGN_RIGHT, 8);
        q->set_position(Vec2(0, 118));
        q->set_size(Vec2(160, 40));
        holder->add(q);
        UIKit::on_tap(cell, [this, item_id] { select(item_id); });
        return cell;
    }

    void select(const std::string& item_id)
    {
        selected = item_id;
        if (grid)
            for (auto c : grid->children())
                static_cast<PanelFrame*>(c)->set_variant(c->name() == "Item_" + item_id ? "boss" : "slot", 10);
        show_detail(item_id);
    }

    void show_detail(const std::string& item_id)
    {
        detail->clear_children();
        if (item_id.empty())
        {
            detail->add(UIKit::label("Select an item to see what it does.", UIKit::T_BODY, UIKit::MUTED, ALIGN_CENTER));
            return;
        }
        const Json& item = DB.item(item_id);
        auto h = UIKit::hbox(UIKit::SP_L);
        detail->add(h);
        auto slot = PanelFrame::make("slot", 10);
        slot->add(UIKit::icon(res(S(item, "icon")), 96));
        h->add(slot);
        auto v = UIKit::vbox(UIKit::SP_XS);
        v->set_h_flags(SIZE_EXPAND_FILL);
        auto top = UIKit::hbox(UIKit::SP_M);
        auto nm = UIKit::label(S(item, "name", item_id), UIKit::T_NAME, UIKit::TEXT, ALIGN_LEFT, 8);
        nm->set_name("DetailName");
        nm->set_h_flags(SIZE_EXPAND_FILL);
        top->add(nm);
        top->add(UIKit::label("x" + UIKit::format_number(GM.item_count(item_id)), UIKit::T_NAME, UIKit::GOLD, ALIGN_RIGHT, 8));
        v->add(top);
        v->add(UIKit::label(S(item, "use"), UIKit::T_SMALL, UIKit::SKY, ALIGN_LEFT, 5));
        v->add(UIKit::wrap_label(S(item, "description"), UIKit::T_SMALL, Col("#e0d6c6")));
        h->add(v);
        auto row = UIKit::hbox(UIKit::SP_M);
        row->alignment = ALIGNMENT_END;
        auto src = UIKit::btn("WHERE TO FIND", "secondary", Vec2(340, 96));
        src->set_name("DetailSources");
        src->pressed.connect([this, item_id] { ItemSources::open(this, item_id); });
        row->add(src);
        // USE only where using it from here makes sense (wisps -> pick a hero to train)
        if (S(item, "category") == "training" && GM.feature_unlocked("training"))
        {
            auto use = UIKit::btn("USE", "primary", Vec2(220, 96));
            use->set_name("DetailUse");
            use->pressed.connect([] {
                UIManager::toast("Pick a hero, then press TRAIN.", "info");
                SceneRouter::go("units");
            });
            row->add(use);
        }
        detail->add(row);
    }

    void currencies()
    {
        struct C { const char* icon; const char* name; long long value; const char* desc; };
        for (auto& c : {C{"assets/icons/gem.png", "Gems", GM.gems(),
                          "Summon heroes at the Embergate. Earned from first clears (5, bosses 25), rank-ups, missions and login rewards."},
                        C{"assets/icons/gold.png", "Gold", GM.gold(), "Pays for training and evolution. Earned from every battle."},
                        C{"assets/icons/soul_shard.png", "Soul Shards", GM.soul_shards(),
                          "Made from duplicate summons. Spend them to train any hero's Burst level."},
                        C{"assets/icons/energy.png", "Energy", GM.energy(), "Spent to enter stages. Refills over time and on every Rank Up."}})
        {
            auto row = PanelFrame::make("plank", 14);
            std::string n = c.name;
            n.erase(std::remove(n.begin(), n.end(), ' '), n.end());
            row->set_name("Currency_" + n);
            auto h = UIKit::hbox(20);
            row->add(h);
            auto slot = PanelFrame::make("slot", 10);
            slot->add(UIKit::icon(c.icon, 96));
            h->add(slot);
            auto v = UIKit::vbox(4);
            v->set_h_flags(SIZE_EXPAND_FILL);
            auto top = UIKit::hbox(12);
            auto nm = UIKit::label(c.name, UIKit::T_NAME, UIKit::TEXT, ALIGN_LEFT, 8);
            nm->set_h_flags(SIZE_EXPAND_FILL);
            top->add(nm);
            top->add(UIKit::label(UIKit::format_number(c.value), UIKit::T_HEAD, UIKit::GOLD, ALIGN_RIGHT, 10));
            v->add(top);
            auto d = UIKit::wrap_label(c.desc, UIKit::T_SMALL, Col("#e0d6c6"));
            d->set_min_w(760);
            v->add(d);
            h->add(v);
            list->add(row);
        }
    }
};
REGISTER_SCREEN("inventory", InventoryScreen)
