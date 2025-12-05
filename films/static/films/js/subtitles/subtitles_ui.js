import { initializeSubtitleSync, stopSubtitleCheck, hideSubtitle } from "./subtitles_sync.js";
import { loadYouTubeAPI } from "./youtube_api.js";

// ------------------------------------------------------------
// ГЛАВНАЯ ТОЧКА ВХОДА
// ------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("subtitle-language-select");
    const toggleSwitch = document.getElementById("subtitles-toggle");
    const editLink = document.getElementById("edit-subtitles-link");

    const videoContainer = document.getElementById("video-player-container");
    const fullscreenBtn = document.getElementById("custom-fullscreen-btn");
    const fullscreenIcon = fullscreenBtn?.querySelector("i");

    const defaultLang = select ? select.value : null;

    // ------------------------------------------------------------
    // 1. Получение карт цветов всех языков
    // ------------------------------------------------------------
    let allSpeakerStyles = {};
    const stylesScript = document.getElementById("all-speaker-styles-data");

    if (stylesScript) {
        try {
            allSpeakerStyles = JSON.parse(stylesScript.textContent);
        } catch (e) {
            console.error("[UI] Ошибка парсинга speakerStyles JSON:", e);
        }
    }

    // ------------------------------------------------------------
    // ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ UI
    // ------------------------------------------------------------

    function updateEditLink(lang) {
        if (!editLink) return;

        const url = new URL(editLink.href);
        url.searchParams.set("lang", lang);

        editLink.href = url.toString();
        editLink.style.display = "block";
    }

    function disableSubtitles() {
        const state = window.subtitleSyncState;

        console.log("[UI] Субтитры выключены.");

        stopSubtitleCheck();
        hideSubtitle();

        if (state) {
            state.currentVttUrl = null;
            state.subtitlesData = [];
        }
    }

    function setupSubtitles(lang) {
        hideSubtitle(); // очистить экран
        stopSubtitleCheck(); // остановить цикл (но player оставляем)

        const speakerStyles = allSpeakerStyles[lang] || {};
        const vttUrl = window.vttUrlTemplate.replace("LANGUAGE_PLACEHOLDER", lang);

        initializeSubtitleSync(
            vttUrl,
            "youtube-player",
            "custom-subtitle-overlay",
            speakerStyles
        );

        updateEditLink(lang);
    }

    // ------------------------------------------------------------
    // 2. Слушатели UI
    // ------------------------------------------------------------

    if (select) {
        select.addEventListener("change", (e) => {
            const lang = e.target.value;

            window.subtitleSyncState.currentVttUrl = null;
            toggleSwitch.checked = true;

            setupSubtitles(lang);
        });
    }

    if (toggleSwitch) {
        toggleSwitch.addEventListener("change", (e) => {
        if (e.target.checked) {
            const lang = select ? select.value : defaultLang;
            setupSubtitles(lang);   // ВКЛЮЧЕНИЕ
        } else {
            disableSubtitles();     // ВЫКЛЮЧЕНИЕ
        }
    });
    }

    // ------------------------------------------------------------
    // 3. Логика Fullscreen-кнопки
    // ------------------------------------------------------------

    function updateFullscreenButtonIcon() {
        if (!fullscreenIcon) return;

        if (document.fullscreenElement) {
            fullscreenIcon.classList.remove("bi-arrows-fullscreen");
            fullscreenIcon.classList.add("bi-fullscreen-exit");
            fullscreenBtn.title = "Выйти из полноэкранного режима";
        } else {
            fullscreenIcon.classList.remove("bi-fullscreen-exit");
            fullscreenIcon.classList.add("bi-arrows-fullscreen");
            fullscreenBtn.title = "На весь экран";
        }
    }

    if (videoContainer && fullscreenBtn) {
        fullscreenBtn.addEventListener("click", () => {
            if (!document.fullscreenElement) {
                videoContainer.requestFullscreen().catch(err => {
                    console.error("[UI] Ошибка fullscreen:", err);
                });
            } else {
                document.exitFullscreen();
            }
        });

        document.addEventListener("fullscreenchange", updateFullscreenButtonIcon);
    }

    // ------------------------------------------------------------
    // 4. Инициализация после загрузки YouTube API
    // ------------------------------------------------------------

    // Django установит этот template-путь в detail.html
    window.vttUrlTemplate = window.vttUrlTemplate || "";

    loadYouTubeAPI().then(() => {
        console.log("[UI] YouTube API готов, запускаем субтитры.");

        const initialLang = select ? select.value : defaultLang;

        if (toggleSwitch) {
            toggleSwitch.checked = true;
            setupSubtitles(initialLang);
        } else {
            disableSubtitles();
        }
    });

});