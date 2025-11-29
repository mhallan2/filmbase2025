/**
 * Инициализирует синхронизацию субтитров с YouTube-плеером.
 * @param {string} vttUrl URL для VTT-файла.
 * @param {string} playerId ID HTML-элемента iframe.
 * @param {string} overlayId ID HTML-элемента оверлея.
 * @param {Object} speakerStyles Объект стилей: { "Имя": "#HEX", ... }
 */
function initializeSubtitleSync(vttUrl, playerId, overlayId, speakerStyles) {
    const overlay = document.getElementById(overlayId);
    let subtitles = [];
    let youtubePlayer;
    let subtitleInterval;
    let isVttLoaded = false;

    // Регулярное выражение для поиска тега спикера VTT: <v SpeakerName>
    const speakerTagRegex = /<v\s*([^>]+)>/;
    // Регулярное выражение для парсинга тега стилей VTT: <c.className>
    const styleTagRegex = /<c\.([^>]+)>/g;

    // --- 1. ЗАГРУЗКА И ПАРСИНГ VTT ---

    /**
     * Конвертирует строку времени VTT (00:00:00.000) в секунды.
     */
    function parseTime(timeStr) {
        if (!timeStr) return 0;
        // Заменяем запятую на точку (для совместимости) и разбиваем
        const parts = timeStr.replace(',', '.').split(':');
        let seconds = 0;

        if (parts.length === 3) {
            // HH:MM:SS.mmm
            seconds += parseFloat(parts[0]) * 3600;
            seconds += parseFloat(parts[1]) * 60;
            seconds += parseFloat(parts[2]);
        } else if (parts.length === 2) {
            // MM:SS.mmm
            seconds += parseFloat(parts[0]) * 60;
            seconds += parseFloat(parts[1]);
        }
        return seconds;
    }

    /**
     * Парсит VTT-файл.
     */
    function parseVTT(vttText) {
        const cues = [];
        const lines = vttText.split('\n').map(line => line.trim());

        let i = 0;
        while (i < lines.length) {
            // Ищем строку с временными метками
            if (lines[i].includes('-->')) {
                const timeLine = lines[i].trim();

                // 1. Ищем имя спикера в строке тайминга ДО очистки
                let speakerName = null;
                const vTagMatch = timeLine.match(speakerTagRegex);
                if (vTagMatch) {
                    speakerName = vTagMatch[1].trim();
                }

                // 2. Очищаем строку тайминга от тега спикера, чтобы не мешал парсить время
                // Было: 00:00:05.000 --> 00:00:07.000 <v Ivonn>
                // Стало: 00:00:05.000 --> 00:00:07.000
                const cleanTimeLine = timeLine.replace(speakerTagRegex, '').trim();

                // 3. Разбиваем по стрелке
                const timeParts = cleanTimeLine.split('-->');

                if (timeParts.length === 2) {
                    const startSec = parseTime(timeParts[0].trim());
                    const endSec = parseTime(timeParts[1].trim());

                    // 4. Текст субтитра
                    i++;
                    let text = lines[i] ? lines[i].trim() : '';

                    // Объединяем многострочные субтитры
                    while (lines[i + 1] && lines[i + 1].trim() !== '') {
                        i++;
                        text += '\n' + lines[i].trim();
                    }

                    if (!isNaN(startSec) && !isNaN(endSec)) {
                        cues.push({
                            start: startSec,
                            end: endSec,
                            text: text,
                            speaker: speakerName // Сохраняем имя!
                        });
                    }
                }
            }
            i++;
        }
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
            console.log(`[SubtitleSync] Загружено субтитров: ${subtitles.length}`);
            // Проверка: выводим первого спикера в консоль
            if(subtitles.length > 0) console.log("Первый спикер:", subtitles[0].speaker);
        })
        .catch(error => {
            console.error('[SubtitleSync] Ошибка загрузки:', error);
            overlay.innerHTML = '<span class="subtitle-line-text" style="color: red;">Ошибка загрузки субтитров.</span>';
        });

    // --- 2. СИНХРОНИЗАЦИЯ С ПЛЕЕРОМ ---

    window.onYouTubeIframeAPIReady = function() {
        youtubePlayer = new YT.Player(playerId, {
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange
            }
        });
    }

    function onPlayerReady(event) {
        if (isVttLoaded) startSubtitleCheck();
    }

    function onPlayerStateChange(event) {
        if (event.data === YT.PlayerState.PLAYING) {
            startSubtitleCheck();
        } else {
            stopSubtitleCheck();
        }
    }

    function startSubtitleCheck() {
        if (!subtitleInterval) {
            subtitleInterval = setInterval(checkSubtitle, 100);
        }
    }

    function stopSubtitleCheck() {
        clearInterval(subtitleInterval);
        subtitleInterval = null;
    }

    // --- 3. ОТОБРАЖЕНИЕ ---

    function checkSubtitle() {
        if (!youtubePlayer || !isVttLoaded || typeof youtubePlayer.getCurrentTime !== 'function') {
            return;
        }
        const currentTime = youtubePlayer.getCurrentTime();
        const currentCue = subtitles.find(cue => currentTime >= cue.start && currentTime < cue.end);

        if (currentCue) {
            displaySubtitle(currentCue);
        } else {
            hideSubtitle();
        }
    }

    function displaySubtitle(cue) {
        const speakerName = cue.speaker;
        let styledText = cue.text;
        const classList = ['subtitle-line-text'];
        let speakerElement = '';
        let dynamicStyleString = '';

        // 1. Обработка ИМЕНИ
        if (speakerName) {
            speakerElement = `<span class="speaker">${speakerName}:</span> `;
            // Ищем цвет в переданном объекте speakerStyles
            const color = speakerStyles[speakerName];
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

    function hideSubtitle() {
        overlay.innerHTML = '';
    }
}