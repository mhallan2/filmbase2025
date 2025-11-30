// ГЛОБАЛЬНОЕ СОСТОЯНИЕ (для управления интервалом и плеером при переключении)
// Используем объект window для сохранения состояния между вызовами функции.
window.subtitleSyncState = window.subtitleSyncState || {
    player: null,
    intervalId: null
};

/**
 * Инициализирует синхронизацию субтитров с YouTube-плеером.
 * @param {string} vttUrl URL для VTT-файла.
 * @param {string} playerId ID HTML-элемента iframe.
 * @param {string} overlayId ID HTML-элемента оверлея.
 * @param {Object} speakerStyles Объект стилей: { "Имя": "#HEX", ... }
 */
function initializeSubtitleSync(vttUrl, playerId, overlayId, speakerStyles) {
    const state = window.subtitleSyncState; // Получаем текущее состояние
    const overlay = document.getElementById(overlayId);
    let subtitles = [];
    let isVttLoaded = false;

    // Регулярное выражение для поиска тега спикера VTT: <v SpeakerName>
    const speakerTagRegex = /<v\s*([^>]+)>/;
    // Регулярное выражение для парсинга тега стилей VTT: <c.className>
    const styleTagRegex = /<c\.([^>]+)>/g;

    // --- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: ОЧИСТКА ПРЕДЫДУЩЕГО СОСТОЯНИЯ ---
    if (state.intervalId) {
        clearInterval(state.intervalId);
        state.intervalId = null;
        console.log('[SubtitleSync] Old interval cleared for language switch.');
    }
    overlay.innerHTML = ''; // Очищаем субтитры на оверлее
    // -----------------------------------------------------------------

    // --- 1. ЗАГРУЗКА И ПАРСИНГ VTT ---

    /**
     * Конвертирует строку времени VTT (00:00:00.000) в секунды.
     */
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

    /**
     * Парсит VTT-файл. (Логика из вашего исходного кода, включая очистку имени спикера)
     */
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
                const vTagMatch = timeLine.match(speakerTagRegex);

                if (vTagMatch) {
                    speakerName = vTagMatch[1].trim();
                    timeLine = timeLine.replace(speakerTagRegex, '').trim();

                    if (cues.length === 0) {
                        console.log("PARSED FIRST SPEAKER:", speakerName);
                    }
                }

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

    // Запрос VTT-файла
    fetch(vttUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(vttText => {
            subtitles = parseVTT(vttText);
            isVttLoaded = true;
            // После загрузки VTT, если плеер уже играет, сразу начинаем синхронизацию
            if (state.player && state.player.getPlayerState() === YT.PlayerState.PLAYING) {
                 startSubtitleCheck();
            } else if (state.player) {
                // Если плеер на паузе или остановлен, проверяем текущее время
                checkSubtitle();
            }
        })
        .catch(error => {
            console.error('[SubtitleSync] Ошибка загрузки:', error);
            overlay.innerHTML = '<span class="subtitle-line-text" style="color: red;">Ошибка загрузки субтитров.</span>';
        });

    // --- 2. СИНХРОНИЗАЦИЯ С ПЛЕЕРОМ (Инициализация только один раз) ---

    // Если плеер еще не инициализирован, создаем его (это произойдет только при первой загрузке страницы)
    if (!state.player) {
        // Определяем глобальный колбэк, который YouTube API вызывает после загрузки
        window.onYouTubeIframeAPIReady = function() {
            state.player = new YT.Player(playerId, {
                events: {
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange
                }
            });
        }
        // Если API уже загрузился до того, как был определен window.onYouTubeIframeAPIReady,
        // вызываем его вручную (простая проверка на случай, если скрипт загрузился быстро)
        if (typeof YT !== 'undefined' && typeof YT.Player === 'function' && !state.player) {
             window.onYouTubeIframeAPIReady();
        }
    }


    function onPlayerReady(event) {
        // Вызывается только один раз при создании плеера.
        if (isVttLoaded) startSubtitleCheck();
    }

    function onPlayerStateChange(event) {
        // Управляет интервалом, используя *текущее* состояние субтитров.
        if (event.data === YT.PlayerState.PLAYING) {
            startSubtitleCheck();
        } else {
            stopSubtitleCheck();
        }
    }

    function startSubtitleCheck() {
        if (!state.intervalId) {
            // Сохраняем ID нового интервала в глобальном состоянии
            state.intervalId = setInterval(checkSubtitle, 100);
        }
    }

    function stopSubtitleCheck() {
        clearInterval(state.intervalId);
        state.intervalId = null;
    }

    // --- 3. ОТОБРАЖЕНИЕ ---

    function checkSubtitle() {
        // Проверяем наличие плеера и загруженных VTT
        if (!state.player || !isVttLoaded || typeof state.player.getCurrentTime !== 'function') {
            return;
        }

        const currentTime = state.player.getCurrentTime();
        const currentCue = subtitles.find(cue => currentTime >= cue.start && currentTime < cue.end);

        if (currentCue) {
            displaySubtitle(currentCue);
        } else {
            hideSubtitle();
        }
    }

    function displaySubtitle(cue) {
        const speakerNameRaw = cue.speaker;
        let styledText = cue.text;
        const classList = ['subtitle-line-text'];
        let speakerElement = '';
        let dynamicStyleString = '';

        // 1. Обработка ИМЕНИ
        if (speakerNameRaw) {
            // ✅ ИСПРАВЛЕНИЕ: Очищаем имя от пробелов, чтобы оно точно совпало с ключом
            const speakerName = speakerNameRaw.trim();

            speakerElement = `<span class="speaker">${speakerName}:</span> `;

            // Ищем цвет в переданном объекте speakerStyles по очищенному имени
            const color = speakerStyles[speakerName];

            if (color) {
                dynamicStyleString = `color: ${color};`;
            }
        }

        // 2. Обработка КЛАССОВ (<c.loud>)
        styledText = styledText.replace(styleTagRegex, (match, classNamesString) => {
             // ... ваш код для обработки классов остается без изменений ...
             const individualClasses = classNamesString.split('.').filter(c => c.trim() !== '');
             individualClasses.forEach(c => {
                 if (c && !classList.includes(c)) classList.push(c);
             });
             return '';
        });
        styledText = styledText.replace(/<\/c>/g, '');

        // 3. Генерация HTML
        const finalClasses = classList.join(' ');
        // Вставляем speakerElement (имя со стилем)
        overlay.innerHTML = `<span class="${finalClasses}" style="${dynamicStyleString}">`
                            + `${speakerElement}${styledText}`
                            + `</span>`;
    }

    function hideSubtitle() {
        overlay.innerHTML = '';
    }
}