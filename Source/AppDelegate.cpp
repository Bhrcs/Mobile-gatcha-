/****************************************************************************
 Copyright (c) 2017-2018 Xiamen Yaji Software Co., Ltd.
 Copyright (c) 2019-present Axmol Engine contributors (see AUTHORS.md).

 https://axmol.dev/

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
 ****************************************************************************/

#include "AppDelegate.h"
#include "app/App.h"
#include "audio/AudioEngine.h"
#ifdef _WIN32
#    include <windows.h>
#    include <cstring>
#endif

using namespace ax;

AppDelegate::AppDelegate() {}

AppDelegate::~AppDelegate() {}

void AppDelegate::initGfxContextAttrs()
{
    GfxContextAttrs attrs = {8, 8, 8, 8, 24, 8, 0};
    RenderView::setGfxContextAttrs(attrs);
}

bool AppDelegate::applicationDidFinishLaunching()
{
    auto director = Director::getInstance();
    auto view = director->getRenderView();
    if (!view)
    {
#if (AX_TARGET_PLATFORM != AX_PLATFORM_ANDROID) && (AX_TARGET_PLATFORM != AX_PLATFORM_IOS)
        view = RenderViewImpl::createWithRect("Cinderbound", ax::Rect(0, 0, 576, 1024), 1.0f, true);
#else
        view = RenderViewImpl::create("Cinderbound");
#endif
        director->setRenderView(view);
    }
#ifdef _WIN32
    // Content/ lives next to the exe. Axmol only looks there when the working directory IS the exe folder, so a
    // shortcut / launcher / "Start in" elsewhere gave a black screen: always search the exe's Content first.
    {
        wchar_t buf[MAX_PATH];
        DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
        std::wstring exe(buf, n);
        std::wstring dir = exe.substr(0, exe.find_last_of(L"\\/") + 1);
        std::string u8(WideCharToMultiByte(CP_UTF8, 0, dir.c_str(), -1, nullptr, 0, nullptr, nullptr), 0);
        WideCharToMultiByte(CP_UTF8, 0, dir.c_str(), -1, u8.data(), (int)u8.size(), nullptr, nullptr);
        u8.resize(strlen(u8.c_str()));
        FileUtils::getInstance()->addSearchPath(u8 + "Content", true);
        if (!FileUtils::getInstance()->isFileExist("data/manifest.json"))
        {
            MessageBoxW(nullptr,
                        L"Cinderbound can't find its Content folder.\n\nExtract the WHOLE zip first (right-click > Extract All), "
                        L"then run Cinderbound.exe from the extracted Cinderbound folder.",
                        L"Cinderbound", MB_OK | MB_ICONERROR);
            director->end();
            return true;
        }
    }
#endif
    director->setStatsDisplay(false);
    director->setAnimationInterval(1.0f / 60);
    App::start();
    return true;
}

void AppDelegate::applicationDidEnterBackground()
{
    Director::getInstance()->stopAnimation();
    AudioEngine::pauseAll();
    if (GM.has_profile()) GM.save();
}

void AppDelegate::applicationWillEnterForeground()
{
    Director::getInstance()->startAnimation();
    AudioEngine::resumeAll();
}

void AppDelegate::applicationWillQuit()
{
    if (GM.has_profile()) GM.save();
}
