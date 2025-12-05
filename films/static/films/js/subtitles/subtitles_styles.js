/**
 * Преобразует список VTT-классов в строку CSS-классов.
 * Например ["bold","italic"] → "bold italic".
 */
export function classesToCss(classes = []) {
    return classes.join(" ");
}

/**
 * Возвращает цвет спикера (если указано в speaker_color_map).
 * Цвет применяется отдельно, в renderSubtitle.
 */
export function resolveSpeakerColor(speaker, map) {
    if (!speaker || !map) return null;
    return map[speaker] || null;
}
