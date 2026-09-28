#pragma once
// SpriteFactory (sprite sheets + meta JSON from tools/make_assets.py) and
// UnitSpriteDisplay (an animated unit inside UI layouts, feet at bottom centre).
#include "ui/Gui.h"

namespace SpriteFactory
{
// sprite_def: {"sheet": path, "meta": path}. Anchor is at the feet (4 px above the frame bottom).
gd::AnimatedSprite* unit(const Json& sprite_def);
gd::Vec2 frame_size(const Json& sprite_def);
float frame_time(const Json& sprite_def, const std::string& anim, int frame);   // seconds until `frame` shows
float anim_length(const Json& sprite_def, const std::string& anim);
gd::AnimatedSprite* effect(const std::string& name);   // one-shot "default" animation, centred
bool has_effect(const std::string& name);
}  // namespace SpriteFactory

class UnitSpriteDisplay : public gd::Control
{
public:
    static UnitSpriteDisplay* make(const Json& sprite_def, float pixel_scale = 4.0f, bool face_left = false,
                                   const std::string& anim = "idle");
    gd::AnimatedSprite* sprite = nullptr;
    void play(const std::string& anim);
protected:
    void size_changed() override;
};
