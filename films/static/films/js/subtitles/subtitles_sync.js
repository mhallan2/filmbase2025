import { createYouTubePlayer } from "./youtube_api.js";
import { loadVTT } from "./subtitles_loader.js";
import { renderSubtitle, clearSubtitle } from "./subtitles_renderer.js";
import { resolveSpeakerColor } from "./subtitles_styles.js";

/*
 * Глобальное состояние — живёт между включениями/выключениями
 */
if (!window.subtitleSyncState) {
    window.subtitleSyncState = {
        player: null,
        subtitles: [],
        currentIndex: -1,
        overlayId: null,
        speakerStyles: {}
    };
}

let state = window.subtitleSyncState;
let intervalId = null;

/**
 * Инициализация субтитров
 */
export async function initializeSubtitleSync(vttUrl, iframeId, overlayId, speakerStyles = {}) {
    state.overlayId = overlayId;
    state.speakerStyles = speakerStyles;

    // Загружаем и парсим VTT
    state.subtitles = await loadVTT(vttUrl);
    state.currentIndex = -1;

    // Создаём плеер только ОДИН раз
    if (!state.player) {
        console.log("[SYNC] Creating YT player...");
        state.player = await createYouTubePlayer(iframeId);
    }

    startLoop();
}

/**
 * Главный цикл синхронизации
 */
function startLoop() {
    stopLoop();

    intervalId = setInterval(() => {
        if (!state.player || !state.subtitles.length) return;

        const t = state.player.getCurrentTime();
        const idx = state.subtitles.findIndex(s => t >= s.start && s.end >= t);

        if (idx !== state.currentIndex) {
            state.currentIndex = idx;

            if (idx === -1) {
                clearSubtitle(state.overlayId);
            } else {
                const s = state.subtitles[idx];
                const color = resolveSpeakerColor(s.speaker, state.speakerStyles);
                renderSubtitle(state.overlayId, s.text, color, s.speaker, s.classes);
            }
        }
    }, 100);
}

function stopLoop() {
    if (intervalId) clearInterval(intervalId);
    intervalId = null;
}

/**
 * Выключение субтитров (но НЕ удаление state!)
 */
export function stopSubtitleCheck() {
    stopLoop();
    clearSubtitle(state.overlayId);

    state.subtitles = [];
    state.currentIndex = -1;
}

/**
 * Просто скрыть — для кнопки Hide
 */
export function hideSubtitle() {
    clearSubtitle(state.overlayId);
}
