"use client"

import type { KeyboardEvent } from "react"
import { useEffect, useId, useRef, useState } from "react"
import { FieldError, FieldLabel } from "./forms"
import { cls, NO_BROWSER_SUGGESTIONS } from "./internals"
import styles from "./styles/primitives.module.css"
import autocomplete from "./styles/autocomplete.module.css"

/** 停止輸入多久才查詢; 連續打字只送出最後一次。 */
const QUERY_DELAY_MS = 250

type AutocompleteInputProps = {
  label: string
  value: string
  required?: boolean
  disabled?: boolean
  error?: string
  /** 依目前輸入的文字取得建議; 空字串代表剛點進欄位, 給最常用的值。 */
  loadOptions: (keyword: string) => Promise<string[]>
  onChange: (value: string) => void
}

/** 建議清單的查詢與開合; 只採用最後一次查詢的結果, 慢回來的舊結果直接丟掉。 */
function useSuggestions(value: string, loadOptions: AutocompleteInputProps["loadOptions"]) {
  const [focused, setFocused] = useState(false)
  const [options, setOptions] = useState<string[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const latest = useRef(0)
  // 呼叫端常傳行內函式; 放進 effect 的相依會讓每次重繪都重查一次。
  const load = useRef(loadOptions)
  useEffect(() => { load.current = loadOptions }, [loadOptions])
  // 選取後 value 會變成選到的值, 不該因此再查一次把清單打開。
  const chosen = useRef<string | null>(null)
  useEffect(() => {
    if (!focused) return
    if (chosen.current === value) { chosen.current = null; return }
    const request = ++latest.current
    const timer = setTimeout(() => {
      load.current(value).then((found) => {
        if (request !== latest.current) return
        setOptions(found); setOpen(found.length > 0); setActive(-1)
      }, () => {
        if (request === latest.current) { setOptions([]); setOpen(false) }
      })
    }, QUERY_DELAY_MS)
    return () => clearTimeout(timer)
  }, [focused, value])
  function close() { latest.current++; setOpen(false); setActive(-1) }
  function choose(option: string) { chosen.current = option; close(); return option }
  function blur() { setFocused(false); close() }
  return { options, open: open && options.length > 0, active, setActive, setOpen, close,
    choose, focus: () => setFocused(true), blur }
}

function keyHandler(list: ReturnType<typeof useSuggestions>, onChange: (value: string) => void) {
  return (event: KeyboardEvent<HTMLInputElement>) => {
    const count = list.options.length
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!count) return
      event.preventDefault()
      if (!list.open) { list.setOpen(true); return }
      list.setActive(event.key === "ArrowDown"
        ? (list.active + 1) % count
        : (list.active <= 0 ? count : list.active) - 1)
    } else if (event.key === "Enter" && list.open && list.active >= 0) {
      event.preventDefault()
      onChange(list.choose(list.options[list.active]))
    } else if (event.key === "Escape" && list.open) {
      event.preventDefault()
      list.close()
    }
  }
}

/**
 * 帶有系統建議的文字輸入框: 點進欄位列出常用值, 打字後列出包含該文字的值, 也可以不選直接輸入。
 *
 * 瀏覽器自己的輸入紀錄與自動填入一律關掉, 清單只放 `loadOptions` 給的值。
 */
export function AutocompleteInput({
  label, value, required, disabled, error, loadOptions, onChange,
}: AutocompleteInputProps) {
  const id = useId()
  const listId = `${id}-listbox`
  const errorId = error ? `${id}-error` : undefined
  const list = useSuggestions(value, loadOptions)
  const activeOption = list.open && list.active >= 0 ? `${id}-option-${list.active}` : undefined
  useEffect(() => {
    if (activeOption) document.getElementById(activeOption)?.scrollIntoView?.({ block: "nearest" })
  }, [activeOption])
  return (
    <label className={styles.field}>
      <FieldLabel label={label} required={required} />
      <span className={autocomplete.control}>
        <input
          id={id}
          className={cls(styles.input, error && styles.inputError)}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={list.open}
          aria-controls={listId}
          aria-activedescendant={activeOption}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
          value={value}
          required={required}
          disabled={disabled}
          {...NO_BROWSER_SUGGESTIONS}
          onFocus={list.focus}
          onBlur={list.blur}
          onKeyDown={keyHandler(list, onChange)}
          onChange={(event) => onChange(event.target.value)}
        />
        {list.open && <ul id={listId} role="listbox" aria-label={label} className={autocomplete.list}>
          {list.options.map((option, index) => <li key={option} id={`${id}-option-${index}`}
            role="option" aria-selected={index === list.active}
            className={cls(autocomplete.option, index === list.active && autocomplete.active)}
            // mousedown 而不是 click: click 之前輸入框已經 blur, 清單會先被收掉。
            onMouseDown={(event) => { event.preventDefault(); onChange(list.choose(option)) }}>
            {option}
          </li>)}
        </ul>}
      </span>
      <FieldError id={errorId} error={error} />
    </label>
  )
}
