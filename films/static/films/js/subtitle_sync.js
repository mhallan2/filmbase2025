// ГЛОБАЛЬНОЕ СОСТОЯНИЕ (для управления интервалом, плеером и данными субтитров)
window.subtitleSyncState = window.subtitleSyncState || {
    player: null,
    intervalId: null,
    currentVttUrl: null,
    subtitlesData: [],
    speakerStyles: {} // Хранилище стилей для текущего языка
};

// Регулярное выражение для поиска тега спикера VTT: <v SpeakerName>
const speakerTagRegex = /<v\s*([^>]+)>/;
// Регулярное выражение для парсинга тега стилей VTT: <c.className>
const styleTagRegex = /<c\.([^>]+)>/g;
const OVERLAY_ID = 'custom-subtitle-overlay';


// =======================================================
//                   УТИЛИТЫ ДЛЯ ПАРСИНГА VTT
// =======================================================

function parseTime(timeStr) {
    if (!timeStr) return 0;
    const parts = timeStr.replace(',', '.').split(':');
    let seconds = 0;

    if (parts.length === 3) {
        seconds += parseFloat(parts[0]) * 3600;
        seconds += parseFloat(parts[1]) * 60;
        seconds += parseFloat(parts[2]);
    } else if (parts.length === 2) {
        seconds += parseFloat(parts[0]) * 60;
        seconds += parseFloat(parts[1]);
    }
    return seconds;
}

function parseVTT(vttText) {
    const cues = [];
    const lines = vttText.split(/\r?\n/).map(line => line.trim());

    let i = 0;
    while (i < lines.length && !lines[i].includes('-->')) {
        i++;
    }

    while (i < lines.length) {
        if (lines[i].includes('-->')) {
            let timeLine = lines[i].trim();
            let speakerName = null;

            const timeParts = timeLine.split('-->');

            if (timeParts.length === 2) {
                const startSec = parseTime(timeParts[0].trim());
                const endSec = parseTime(timeParts[1].trim().split(' ')[0]);

                i++;
                let text = lines[i] ? lines[i].trim() : '';

                while (lines[i + 1] && lines[i + 1].trim() !== '') {
                    i++;
                    text += ' ' + lines[i].trim();
                }

                const vTagMatch = text.match(speakerTagRegex);
                if (vTagMatch) {
                    speakerName = vTagMatch[1].trim();
                    text = text.replace(speakerTagRegex, '').trim();
                }

                if (!isNaN(startSec) && !isNaN(endSec) && text) {
                    cues.push({
                        start: startSec,
                        end: endSec,
                        text: text,
                        speaker: speakerName
                    });
                }
            }
        }
        i++;
    }

    console.log(`[SubtitleSync] Загружено субтитров: ${cues.length}`);
    return cues;
}

// =======================================================
//                ФУНКЦИИ УПРАВЛЕНИЯ ИНТЕРВАЛОМ
// =======================================================

function startSubtitleCheck() {
    const state = window.subtitleSyncState;
    if (!state.intervalId) {
        state.intervalId = setInterval(checkSubtitle, 100);
    }
}

function stopSubtitleCheck() {
    const state = window.subtitleSyncState;
    if (state.intervalId) {
        clearInterval(state.intervalId);
        state.intervalId = null;
    }
}

// =======================================================
//                ФУНКЦИИ ОТОБРАЖЕНИЯ И ПРОВЕРКИ
// =======================================================

function hideSubtitle() {
    const overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.innerHTML = '';
}

function displaySubtitle(cue) {
    const state = window.subtitleSyncState;
    const overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) return;

    const speakerNameRaw = cue.speaker;
    let styledText = cue.text;
    const classList = ['subtitle-line-text'];
    let speakerElement = '';
    let dynamicStyleString = '';

    // 1. Обработка ИМЕНИ
    if (speakerNameRaw) {
        const speakerName = speakerNameRaw.trim();
        speakerElement = `<span class="speaker">${speakerName}:</span> `;
        // Читаем стили из глобального состояния
        const color = state.speakerStyles[speakerName];

        if (color) {
            dynamicStyleString = `color: ${color};`;
        }
    }

    // 2. Обработка КЛАССОВ (<c.loud>)
    styledText = styledText.replace(styleTagRegex, (match, classNamesString) => {
         const individualClasses = classNamesString.split('.').filter(c => c.trim() !== '');
         individualClasses.forEach(c => {
             if (c && !classList.includes(c)) classList.push(c);
         });
         return '';
    });
    styledText = styledText.replace(/<\/c>/g, '');

    // 3. Генерация HTML
    const finalClasses = classList.join(' ');
    overlay.innerHTML = `<span class="${finalClasses}" style="${dynamicStyleString}">`
                        + `${speakerElement}${styledText}`
                        + `</span>`;
}

function checkSubtitle() {
    const state = window.subtitleSyncState;
    // Проверяем наличие плеера И ГЛОБАЛЬНЫХ ДАННЫХ
    if (!state.player || state.subtitlesData.length === 0 || typeof state.player.getCurrentTime !== 'function') {
        return;
    }

    const currentTime = state.player.getCurrentTime();
    // Ищем в ГЛОБАЛЬНОМ массиве
    const currentCue = state.subtitlesData.find(cue => currentTime >= cue.start && currentTime < cue.end);

    if (currentCue) {
        displaySubtitle(currentCue);
    } else {
        hideSubtitle();
    }
}

// =======================================================
//                ОБРАБОТЧИКИ СОБЫТИЙ ПЛЕЕРА
// =======================================================

function onPlayerReady(event) {
    const state = window.subtitleSyncState;
    // Проверяем, есть ли данные в глобальном состоянии. Если данные уже загружены, начинаем проверку.
    if (state.subtitlesData.length > 0) startSubtitleCheck();
}

function onPlayerStateChange(event) {
    if (event.data === YT.PlayerState.PLAYING) {
        startSubtitleCheck();
    } else {
        stopSubtitleCheck();
        // При паузе/остановке также проверяем, нужно ли показать субтитр
        if (event.data === YT.PlayerState.PAUSED) {
            checkSubtitle();
        }
    }
}

// =======================================================
//             ГЛАВНАЯ ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ
// =======================================================

function initializeSubtitleSync(vttUrl, playerId, overlayId, incomingSpeakerStyles) {
    const state = window.subtitleSyncState;

    // 🛑 1. Идемпотентность и проверка готовности плеера
    const isPlayerReady = state.player && typeof state.player.getPlayerState === 'function';

    if (state.currentVttUrl === vttUrl) {
        console.warn(`[SubtitleSync] Same VTT URL used: ${vttUrl}. Skipping re-load.`);
        if (isPlayerReady && state.player.getPlayerState() === YT.PlayerState.PLAYING) {
             startSubtitleCheck();
        }
        return;
    }

    // 2. Обновление состояния: очистка старого
    if (state.intervalId) {
        clearInterval(state.intervalId);
        state.intervalId = null;
        console.log('[SubtitleSync] Old interval cleared for new VTT load.');
    }

    state.currentVttUrl = vttUrl; 
    state.subtitlesData = [];
    state.speakerStyles = incomingSpeakerStyles; 
    const overlay = document.getElementById(overlayId);
    if (overlay) overlay.innerHTML = '';


    // 3. Загрузка VTT-файла
    fetch(vttUrl)
        .then(response => {
            if (!response.ok) {
                state.currentVttUrl = null;
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(vttText => {
            state.subtitlesData = parseVTT(vttText);

            // Запуск синхронизации после загрузки
            if (isPlayerReady && state.player.getPlayerState() === YT.PlayerState.PLAYING) {
                 startSubtitleCheck();
            } else if (state.player) {
                checkSubtitle();
            }
        })
        .catch(error => {
            console.error('[SubtitleSync] Ошибка загрузки:', error);
            if (overlay) {
                overlay.innerHTML = '<span class="subtitle-line-text" style="color: red;">Ошибка загрузки субтитров.</span>';
            }
        });

    // 4. Инициализация плеера (только один раз)
    if (!state.player) {
        // 🛑 КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Создаем плеер сразу, если YT API готов.
        // Мы УДАЛИЛИ логику перезаписи window.onYouTubeIframeAPIReady из этого файла.
        if (typeof YT !== 'undefined' && typeof YT.Player === 'function') {
            state.player = new YT.Player(playerId, {
                events: {
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange
                }
            });
        }
    }
}