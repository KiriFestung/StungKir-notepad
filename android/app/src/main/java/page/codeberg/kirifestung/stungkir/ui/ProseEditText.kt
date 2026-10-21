// StungKir для Android. Copyright (C) 2026 KiriFesTung, GPL-3.0-or-later
package page.codeberg.kirifestung.stungkir.ui

import android.annotation.SuppressLint
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Typeface
import android.text.Editable
import android.text.InputType
import android.text.Spanned
import android.text.TextPaint
import android.text.TextWatcher
import android.text.style.CharacterStyle
import android.text.style.MetricAffectingSpan
import android.util.TypedValue
import android.view.Gravity
import android.widget.EditText
import page.codeberg.kirifestung.stungkir.logic.TextRules
import page.codeberg.kirifestung.stungkir.logic.TextRules.Kind
import page.codeberg.kirifestung.stungkir.logic.UndoStack

/** Цвет и подложка (без смены размеров - дёшево для разметки). */
private class ColorMark(val fg: Int?, val bg: Int?) : CharacterStyle() {
    override fun updateDrawState(tp: TextPaint) {
        if (fg != null) tp.color = fg
        if (bg != null) tp.bgColor = bg
    }
}

/** Курсив, жирный, крупнее - меняют ширину букв. */
private class ShapeMark(val bold: Boolean, val italic: Boolean, val scale: Float) : MetricAffectingSpan() {
    override fun updateDrawState(tp: TextPaint) = apply(tp)
    override fun updateMeasureState(tp: TextPaint) = apply(tp)
    private fun apply(tp: TextPaint) {
        if (scale != 1f) tp.textSize = tp.textSize * scale
        val old = tp.typeface ?: Typeface.DEFAULT
        val style = old.style or (if (bold) Typeface.BOLD else 0) or (if (italic) Typeface.ITALIC else 0)
        if (style == old.style) return
        val face = Typeface.create(old, style)
        tp.typeface = face
        val missing = style and face.style.inv()
        if (missing and Typeface.BOLD != 0) tp.isFakeBoldText = true
        if (missing and Typeface.ITALIC != 0) tp.textSkewX = -0.22f
    }
}

/**
 * Поле главы: обычное поле Android (проверка орфографии и подсказки клавиатуры работают как везде),
 * плюс разметка как на компьютере, починка вставки, отмена правок и подсчёт слов.
 */
@SuppressLint("ViewConstructor")
class ProseEditText(context: Context) : EditText(context) {
    var palette: Palette = Themes.byName(null)
    var names: TextRules.Names = TextRules.Names(emptyList())
    var showPunctuation = true
    var showRepeats = true
    val undoStack = UndoStack()

    /** Правка сделана: (сколько слов прибавилось набором, сколько вставлено из буфера). */
    var onEdited: ((typed: Int, pasted: Int) -> Unit)? = null
    var onUndoState: (() -> Unit)? = null

    private var loading = false
    private var replaying = false
    private var pasting = false
    private var removed = ""
    private var oldParagraphWords = 0
    private var typedTo = -1

    init {
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or
            InputType.TYPE_TEXT_FLAG_CAP_SENTENCES or InputType.TYPE_TEXT_FLAG_AUTO_CORRECT
        isSingleLine = false
        setHorizontallyScrolling(false)
        gravity = Gravity.TOP or Gravity.START
        background = null
        isVerticalScrollBarEnabled = true
        addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence, start: Int, count: Int, after: Int) {
                if (loading) return
                removed = s.subSequence(start, start + count).toString()
                val (a, b) = paragraph(s, start, start + count)
                oldParagraphWords = TextRules.countWords(s.subSequence(a, b))
            }

            override fun onTextChanged(s: CharSequence, start: Int, before: Int, count: Int) {
                if (loading) return
                val inserted = s.subSequence(start, start + count).toString()
                typedTo = start + count
                val (a, b) = paragraph(s, start, start + count)
                val newWords = TextRules.countWords(s.subSequence(a, b))
                // большая вставка разом (буфер обмена с клавиатуры) - тоже вставка, а не набор
                val pasted = if (pasting || inserted.length > 300) TextRules.countWords(inserted) else 0
                if (!replaying) {
                    undoStack.record(start, removed, inserted)
                    if (pasting) undoStack.seal()
                }
                post { highlight(a, a + (b - a)) }
                onEdited?.invoke(newWords - oldParagraphWords - pasted, pasted)
                onUndoState?.invoke()
            }

            override fun afterTextChanged(s: Editable) {}
        })
    }

    fun applyLook(p: Palette, fontName: String, sizeSp: Int, spacing: Float) {
        palette = p
        setTextColor(p.text.toInt())
        setHintTextColor(p.dim.toInt())
        highlightColor = p.select.toInt()
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp.toFloat())
        setLineSpacing(0f, spacing)
        typeface = fontFor(context, fontName)
        rehighlightAll()
    }

    /** Загрузить главу: без подсчёта слов и без отмены. */
    fun load(text: String, cursor: Int) {
        loading = true
        try {
            setText(text)
        } finally {
            loading = false
        }
        undoStack.clear()
        setSelection(cursor.coerceIn(0, text.length))
        rehighlightAll()
        onUndoState?.invoke()
    }

    /** Подменить текст снаружи (пришёл с компьютера), курсор - примерно туда же. */
    fun replaceAll(text: String) {
        val at = selectionStart
        load(text, at)
    }

    fun undo() = replay(undoStack.undo())
    fun redo() = replay(undoStack.redo())

    private fun replay(edit: UndoStack.Edit?) {
        edit ?: return
        val e = editableText
        if (edit.start + edit.removed.length > e.length) return
        replaying = true
        try {
            e.replace(edit.start, edit.start + edit.removed.length, edit.inserted)
        } finally {
            replaying = false
        }
        setSelection((edit.start + edit.inserted.length).coerceIn(0, e.length))
        onUndoState?.invoke()
    }

    /** Вставить на место выделения (кнопки над клавиатурой). Если обёртка - выделенное оказывается внутри. */
    fun insertAround(before: String, after: String = "") {
        val e = editableText
        val a = minOf(selectionStart, selectionEnd).coerceAtLeast(0)
        val b = maxOf(selectionStart, selectionEnd).coerceAtLeast(0)
        val inner = e.subSequence(a, b).toString()
        undoStack.seal()
        e.replace(a, b, before + inner + after)
        undoStack.seal()
        if (inner.isEmpty()) setSelection(a + before.length) else setSelection(a + before.length + inner.length + after.length)
    }

    /** Реплика: «— » в начале абзаца, а внутри строки - тире с пробелами. */
    fun insertDash() {
        val e = editableText
        val at = selectionStart.coerceAtLeast(0)
        val lineStart = e.lastIndexOf('\n', at - 1) + 1
        val atLineStart = e.subSequence(lineStart, at).isBlank()
        val before = if (at > 0) e[at - 1] else '\n'
        insertAround(if (atLineStart) "— " else if (before == ' ') "— " else " — ")
    }

    override fun onTextContextMenuItem(id: Int): Boolean {
        if (id == android.R.id.paste || id == android.R.id.pasteAsPlainText) {
            val clip = (context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).primaryClip
            val raw = clip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(context)?.toString()
            if (raw != null) {
                val clean = TextRules.cleanPasted(raw)
                val e = editableText
                val a = minOf(selectionStart, selectionEnd).coerceAtLeast(0)
                val b = maxOf(selectionStart, selectionEnd).coerceAtLeast(0)
                undoStack.seal()
                pasting = true
                try {
                    e.replace(a, b, clean)
                } finally {
                    pasting = false
                }
                setSelection((a + clean.length).coerceAtMost(e.length))
                return true
            }
        }
        return super.onTextContextMenuItem(id)
    }

    override fun onSelectionChanged(selStart: Int, selEnd: Int) {
        super.onSelectionChanged(selStart, selEnd)
        // курсор ушёл не туда, где кончился набор - следующая правка отдельная
        // (при создании поля стека ещё нет, отсюда ?.)
        if (selStart != typedTo || selEnd != typedTo) undoStack?.seal()
    }

    // ---------------- разметка ----------------
    private fun paragraph(s: CharSequence, from: Int, to: Int): Pair<Int, Int> {
        var a = from.coerceIn(0, s.length)
        while (a > 0 && s[a - 1] != '\n') a--
        var b = to.coerceIn(a, s.length)
        while (b < s.length && s[b] != '\n') b++
        return a to b
    }

    fun rehighlightAll() {
        val e = editableText ?: return
        for (span in e.getSpans(0, e.length, CharacterStyle::class.java)) {
            if (span is ColorMark || span is ShapeMark) e.removeSpan(span)
        }
        highlight(0, e.length)
    }

    private fun highlight(from: Int, to: Int) {
        val e = editableText ?: return
        val (a, b) = paragraph(e, from, to)
        for (span in e.getSpans(a, b, CharacterStyle::class.java)) {
            if (span !is ColorMark && span !is ShapeMark) continue
            val s = e.getSpanStart(span)
            val f = e.getSpanEnd(span)
            if (f > a || s >= a && s <= b) e.removeSpan(span)
        }
        val p = palette
        val dialogue = p.dialogue.toInt()
        val starsColor = mix(p.border, p.text, 0.3)
        var lineStart = a
        while (lineStart <= b) {
            var lineEnd = e.indexOf('\n', lineStart)
            if (lineEnd < 0 || lineEnd > b) lineEnd = b
            val line = e.subSequence(lineStart, lineEnd).toString()
            for (span in TextRules.lineSpans(line, names)) {
                val s = lineStart + span.start
                val f = lineStart + span.end
                if (f <= s) continue
                val mark: Any = when (span.kind) {
                    Kind.DIALOGUE -> ColorMark(dialogue, null)
                    Kind.PUNCT -> if (showPunctuation) ColorMark(p.punct.toInt(), null) else continue
                    Kind.MARKER -> ColorMark(p.marker.toInt(), p.markerBg.toInt())
                    Kind.ITALIC -> ShapeMark(bold = false, italic = true, scale = 1f)
                    Kind.BOLD -> ShapeMark(bold = true, italic = false, scale = 1f)
                    Kind.STARS, Kind.SCENE -> ColorMark(starsColor, null)
                    Kind.HEADING -> ShapeMark(bold = true, italic = false, scale = 1.18f)
                    Kind.REPEAT -> if (showRepeats) ColorMark(null, p.repeatBg.toInt()) else continue
                }
                e.setSpan(mark, s, f, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            lineStart = lineEnd + 1
        }
    }

    companion object {
        fun mix(a: Long, b: Long, t: Double): Int {
            fun ch(c: Long, shift: Int) = ((c shr shift) and 0xFF).toInt()
            fun m(shift: Int) = (ch(a, shift) * (1 - t) + ch(b, shift) * t).toInt().coerceIn(0, 255)
            return (0xFF shl 24) or (m(16) shl 16) or (m(8) shl 8) or m(0)
        }

        fun fontFor(context: Context, name: String): Typeface = when (name) {
            "Literata" -> context.resources.getFont(page.codeberg.kirifestung.stungkir.R.font.literata)
            "PT Serif" -> context.resources.getFont(page.codeberg.kirifestung.stungkir.R.font.pt_serif)
            "Системный без засечек" -> Typeface.SANS_SERIF
            else -> Typeface.SERIF
        }
    }
}
