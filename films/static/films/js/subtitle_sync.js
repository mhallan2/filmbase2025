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
        // Используем надежный разделитель, чтобы учесть \r\n (Windows) и \n (Linux/Unix)
        const lines = vttText.split(/\r?\n/).map(line => line.trim());

        let i = 0;
        // Пропускаем заголовок 'WEBVTT' и пустые строки
        while (i < lines.length && !lines[i].includes('-->')) {
            i++;
        }

        while (i < lines.length) {
            if (lines[i].includes('-->')) {
                let timeLine = lines[i].trim();

                // 1. Извлечение имени спикера из строки тайминга
                let speakerName = null;
                // speakerTagRegex = /<v\s*([^>]+)>/;
                const vTagMatch = timeLine.match(speakerTagRegex);

                if (vTagMatch) {
                    // Группа 1 (vTagMatch[1]) содержит имя спикера.
                    speakerName = vTagMatch[1].trim();

                    // 2. ОЧИЩАЕМ строку тайминга от тега спикера
                    timeLine = timeLine.replace(speakerTagRegex, '').trim();

                    // 🚨 КОНТРОЛЬНЫЙ ЛОГ: Имя должно выводиться здесь
                    // Теперь мы можем заменить ваш старый лог 'Первый спикер: null'
                    if (cues.length === 0) {
                        console.log("PARSED FIRST SPEAKER:", speakerName);
                    }
                }

                // 3. Разбиваем по стрелке
                const timeParts = timeLine.split('-->');

                if (timeParts.length === 2) {
                    const startSec = parseTime(timeParts[0].trim());
                    // Вторая часть: берем только время (отбрасывая возможные настройки VTT)
                    const endSec = parseTime(timeParts[1].trim().split(' ')[0]);

                    // 4. Текст субтитра
                    i++;
                    let text = lines[i] ? lines[i].trim() : '';

                    // Объединяем многострочные субтитры (ищем пустую строку)
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

        // 🚨 КОНТРОЛЬНЫЙ ЛОГ: Проверяем общее количество загруженных субтитров
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
    const speakerNameRaw = cue.speaker; // Имя, как пришло из VTT
    let styledText = cue.text;
    const classList = ['subtitle-line-text'];
    let speakerElement = '';
    let dynamicStyleString = '';

    // 1. Обработка ИМЕНИ
    if (speakerNameRaw) {
        // 🛑 ИСПРАВЛЕНИЕ #1: Очищаем имя от пробелов, чтобы оно точно совпало
        // с ключом в speakerStyles (который был введен без пробелов в админке)
        const speakerName = speakerNameRaw.trim();

        // 🛑 ИСПРАВЛЕНИЕ #2: Создаем элемент спикера с очищенным именем
        speakerElement = `<span class=\"speaker\">${speakerName}:</span> `;

        // Ищем цвет в переданном объекте speakerStyles по очищенному имени
        const color = speakerStyles[speakerName];

        if (color) {
            // Применяем inline-стиль к обертке
            dynamicStyleString = `color: ${color};`;
        }
    }

    // 2. Обработка КЛАССОВ (<c.loud>) - Оставляем как есть
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
    // Вставляем speakerElement (имя со стилем), если оно было найдено
    overlay.innerHTML = `<span class=\"${finalClasses}\" style=\"${dynamicStyleString}\">`
                        + `${speakerElement}${styledText}`
                        + `</span>`;
}

    function hideSubtitle() {
        overlay.innerHTML = '';
    }
}