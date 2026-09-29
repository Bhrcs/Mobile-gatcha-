#include "Sprites.h"
#include "logic/Database.h"

namespace SpriteFactory
{
static const Json& meta_of(const Json& def) { return DB.sprite_meta(S(def, "meta")); }

gd::AnimatedSprite* unit(const Json& def)
{
    auto s = gd::AnimatedSprite::create();
    auto tex = gd::texture(S(def, "sheet"));
    const Json& meta = meta_of(def);
    if (!tex || !meta.contains("frame_size"))
    {
        Platform::log("Missing sprite sheet/meta: " + S(def, "sheet"));
        std::vector<ax::Rect> r{ax::Rect(0, 0, 4, 4)};
        for (auto a : {"idle", "attack", "hit", "victory", "ko", "burst", "death"}) s->add_animation(a, r, gd::white_texture(), 1, true);
        s->setColor(ax::Color3B(255, 0, 255));
        s->setScale(8);
        s->play("idle");
        return s;
    }
    float fw = (float)I(at(meta["frame_size"], 0), 48), fh = (float)I(at(meta["frame_size"], 1), 48);
    for (auto& [name, a] : O(meta, "animations").items())
    {
        std::vector<ax::Rect> regions;
        int row = I(a, "row", 0);
        for (int i = 0; i < I(a, "frames", 1); ++i) regions.push_back(ax::Rect(i * fw, row * fh, fw, fh));
        s->add_animation(name, regions, tex, (float)F(a, "fps", 8), B(a, "loop", false));
    }
    const Json& pv = at(meta, "pivot");   // Phase 6 sheets name their feet pivot; old 48px sheets stand 4px up
    s->setAnchorPoint(pv.is_array() ? gd::Vec2((float)F(at(pv, 0), fw / 2) / fw, 1.0f - (float)F(at(pv, 1), fh - 4) / fh)
                                    : gd::Vec2(0.5f, 4.0f / fh));
    return s;
}

gd::Vec2 frame_size(const Json& def)
{
    const Json& m = meta_of(def);
    if (!m.contains("frame_size")) return gd::Vec2(48, 48);
    return gd::Vec2((float)I(at(m["frame_size"], 0), 48), (float)I(at(m["frame_size"], 1), 48));
}

float frame_time(const Json& def, const std::string& anim, int frame)
{
    const Json& a = at(O(meta_of(def), "animations"), anim);
    return a.is_object() ? float(frame) / std::max(1.0f, (float)F(a, "fps", 8)) : 0.0f;
}

float anim_length(const Json& def, const std::string& anim)
{
    const Json& a = at(O(meta_of(def), "animations"), anim);
    return a.is_object() ? float(I(a, "frames", 1)) / std::max(1.0f, (float)F(a, "fps", 8)) : 0.0f;
}

static const Json& effects_meta() { return DB.sprite_meta("assets/effects/effects.json"); }

bool has_effect(const std::string& name) { return effects_meta().contains(name); }

gd::AnimatedSprite* effect(const std::string& name)
{
    auto s = gd::AnimatedSprite::create();
    const Json& m = at(effects_meta(), name);
    auto tex = gd::texture("assets/effects/" + name + ".png");
    if (!tex || !m.is_object()) return s;
    float fw = (float)I(at(m["frame_size"], 0), 32), fh = (float)I(at(m["frame_size"], 1), 32);
    std::vector<ax::Rect> regions;
    for (int i = 0; i < I(m, "frames", 1); ++i) regions.push_back(ax::Rect(i * fw, 0, fw, fh));
    s->add_animation("default", regions, tex, (float)F(m, "fps", 12), false);
    return s;
}
}  // namespace SpriteFactory

UnitSpriteDisplay* UnitSpriteDisplay::make(const Json& def, float k, bool face_left, const std::string& anim)
{
    auto d = gd::make<UnitSpriteDisplay>();
    gd::Vec2 fs = SpriteFactory::frame_size(def);
    k = std::max(1.0f, std::round(k * 48.0f / fs.y));   // UI scales are authored for 48px sheets; keep whole-pixel scaling
    d->set_custom_min(gd::Vec2(fs.x * k * 0.7f, fs.y * k * 0.8f));
    d->set_mouse_filter(gd::MOUSE_IGNORE);
    d->sprite = SpriteFactory::unit(def);
    d->sprite->setScale(k);
    d->sprite->setFlippedX(face_left);
    d->addChild(d->sprite);
    d->sprite->play(anim);
    d->size_changed();
    return d;
}

void UnitSpriteDisplay::play(const std::string& anim)
{
    if (sprite && sprite->has_animation(anim)) sprite->play(anim);
}

void UnitSpriteDisplay::size_changed()
{
    if (!sprite) return;
    gd::Vec2 s(std::max(size().x, custom_min().x), std::max(size().y, custom_min().y));
    // Axmol origin is the bottom-left corner: feet at the bottom centre
    sprite->setPosition(s.x / 2, size().y > 0 ? 0 : size().y - s.y);
}
