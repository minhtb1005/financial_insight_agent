"use client"
import { useEffect, useState } from "react"
import { Toaster as Sonner, type ToasterProps } from "sonner"

// Wrapper doc .dark class do ThemeToggle quan ly (khong dung next-themes
// provider, giu nguyen theme-toggle hien tai).
function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(false)
  useEffect(() => {
    const read = () => setIsDark(document.documentElement.classList.contains("dark"))
    read()
    const obs = new MutationObserver(read)
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })
    return () => obs.disconnect()
  }, [])
  return isDark
}

const Toaster = ({ ...props }: ToasterProps) => {
  const isDark = useIsDark()
  return <Sonner theme={isDark ? "dark" : "light"} richColors closeButton {...props} />
}

export { Toaster }
