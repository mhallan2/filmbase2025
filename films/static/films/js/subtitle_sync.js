/**
 * Инициализирует синхронизацию субтитров с YouTube-плеером.
 * * @param {string} vttUrl URL для VTT-файла, который отдает Django (views.get_subtitles).
 * @param {string} playerId ID HTML-элемента iframe (YouTube-плеер).
 * @param {string} overlayId ID HTML-элемента для отображения субтитров.
 * @param {Object} speakerStyles Объект, содержащий стили для спикеров:
 * { "SpeakerName": { "color": "...", "class": "css-class" }, ... }
 */
function initializeSubtitleSync(vttUrl, playerId, overlayId, speakerStyles) {
    const overlay = document.getElementById(overlayId);
    let subtitles = [];
    let youtubePlayer;
    let subtitleInterval;
    let isVttLoaded = false;

    // Регулярное выражение для парсинга тега спикера VTT: <v SpeakerName>
    const speakerTagRegex = /^<v\s*([^>]+)>/;
    // Регулярное выражение для парсинга тега стилей VTT: <c.className>
    const styleTagRegex = /<c\.([^>]+)>/g;

    // --- 1. ЗАГРУЗКА И ПАРСИНГ VTT ---

    /**
     * Парсит VTT-файл (текст) в массив объектов субтитров.
     * @param {string} vttText Содержимое VTT-файла.
     */
    function parseVTT(vttText) {
        const cues = [];
        // Разделяем VTT по строкам, игнорируя заголовок WEBVTT
        const lines = vttText.split('\n');

        let i = 0;
        while (i < lines.length) {
            // Ищем строку с временными метками
            if (lines[i].includes('-->')) {
                const timeLine = lines[i].trim();
                const [startStr, endStr] = timeLine.split('-->').map(s => s.trim());

                // Парсинг времени в секунды
                const startSec = parseTime(startStr);
                const endSec = parseTime(endStr);

                // Следующая строка - текст субтитра
                let text = lines[++i] ? lines[i].trim() : '';

                // Объединяем многострочные субтитры (если есть пустые строки)
                while (lines[++i] && lines[i].trim() !== '') {
                    text += '\n' + lines[i].trim();
                }

                if (!isNaN(startSec) && !isNaN(endSec)) {
                    cues.push({
                        start: startSec,
                        end: endSec,
                        text: text
                    });
                }
            }
            i++;
        }
        return cues;
    }

    /**
     * Конвертирует строку времени VTT (00:00:00.000) в секунды.
     */
    function parseTime(timeStr) {
        const parts = timeStr.split(':');
        let seconds = 0;
        if (parts.length === 3) {
            seconds += parseFloat(parts[0]) * 3600; // Часы
            seconds += parseFloat(parts[1]) * 60;   // Минуты
            seconds += parseFloat(parts[2]);        // Секунды (включая миллисекунды)
        } else if (parts.length === 2) {
            seconds += parseFloat(parts[0]) * 60;   // Минуты
            seconds += parseFloat(parts[1]);        // Секунды
        }
        return seconds;
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
            console.log(`[SubtitleSync] VTT loaded and parsed. Total cues: ${subtitles.length}`);
        })
        .catch(error => {
            console.error('[SubtitleSync] Error loading VTT:', error);
            overlay.innerHTML = '<span class="subtitle-line" style="color: red;">Ошибка загрузки субтитров.</span>';
        });

    // --- 2. СИНХРОНИЗАЦИЯ С ПЛЕЕРОМ (API YouTube) ---

    // Функция, которая вызывается, когда YouTube Iframe API загружен
    window.onYouTubeIframeAPIReady = function() {
        youtubePlayer = new YT.Player(playerId, {
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange
            }
        });
    }

    function onPlayerReady(event) {
        // Устанавливаем интервал проверки только после готовности плеера
        if (isVttLoaded) {
             startSubtitleCheck();
        }
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
            subtitleInterval = setInterval(checkSubtitle, 100); // Проверка каждые 100 мс
        }
    }

    function stopSubtitleCheck() {
        clearInterval(subtitleInterval);
        subtitleInterval = null;
    }

    // --- 3. ЛОГИКА ОТОБРАЖЕНИЯ И СТИЛИЗАЦИИ ---

    /**
     * Проверяет, какой субтитр должен находится в данный момент времени
     */
    function checkSubtitle() {
        if (!youtubePlayer || !isVttLoaded || typeof youtubePlayer.getCurrentTime !== 'function') {
            return;
        }

        const currentTime = youtubePlayer.getCurrentTime();
        let currentCue = null;

        // Находим активный субтитр
        for (const cue of subtitles) {
            if (currentTime >= cue.start && currentTime < cue.end) {
                currentCue = cue;
                break;
            }
        }

        if (currentCue) {
            displaySubtitle(currentCue);
        } else {
            hideSubtitle();
        }
    }

    /**
     * Обрабатывает и отображает субтитр, применяя стили спикеров.
     * @param {Object} cue Объект субтитра { start, end, text }.
     */
    function displaySubtitle(cue) {
        // Регулярные выражения (предположим, они определены глобально, как и должно быть)
        // const speakerTagRegex = /<v\s+([^>]+)>/;
        // const styleTagRegex = /<c\.([^>]+)>/g;

        // Ищем имя спикера: <v SpeakerName>
        const speakerMatch = cue.text.match(speakerTagRegex);
        let speakerName = null;
        let cleanedText = cue.text; // Текст без тегов VTT

        // 1. Создаем массив классов, начиная с БАЗОВОГО класса
        // Используем класс "subtitle-line-text", который СТИЛИЗОВАН в CSS
        const classList = ['subtitle-line-text'];

        // Элемент, который будет содержать имя спикера
        let speakerElement = '';

        if (speakerMatch) {
            speakerName = speakerMatch[1].trim();
            // Убираем тег спикера из текста, который будет отображаться
            cleanedText = cleanedText.replace(speakerTagRegex, '').trim();

            // 2. Находим CSS-класс для этого спикера (если нужно)
            if (speakerName in speakerStyles && speakerStyles[speakerName].class) {
                classList.push(speakerStyles[speakerName].class);
            }

            // Формируем HTML для имени спикера, используя класс .speaker
            speakerElement = `<span class="speaker">${speakerName}:</span> `;
        }

        // 3. Обрабатываем тег стилей VTT: <c.className>
        let styledText = cleanedText;
        let additionalStyleClasses = '';

        // VTT-теги вложенности (<b>, <i>) обрабатываем вторым этапом
        // Здесь мы ищем VTT-классы (например, <c.bold> или <c.loud>)
        styledText = styledText.replace(styleTagRegex, (match, className) => {
             // Классы из VTT (например, 'loud', 'bold') добавляются к общим классам контейнера
             classList.push(className);
             // Удаляем тег VTT из отображаемого текста
             return '';
        });

        // VTT-теги закрытия (</c>) просто удаляем
        styledText = styledText.replace(/<\/c>/g, '');

        // 4. Генерируем финальную строку классов
        const finalClasses = classList.filter(c => c).join(' ');

        // Создаем HTML-элемент для отображения
        // Теперь используется:
        // 1. Правильный класс CSS: subtitle-line-text
        // 2. Чистая строка классов (без лишних пробелов)
        // 3. Имя спикера в отдельном <span>
        overlay.innerHTML = `<span class="${finalClasses}">${speakerElement}${styledText}</span>`;
    }

    function hideSubtitle() {
        overlay.innerHTML = '';
    }
}