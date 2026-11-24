"""Símbolos del botón «Símbolo» (lista pura, con prueba)."""

SYMBOL_GROUPS: dict[str, str] = {
    "Matemáticas": "± × ÷ = ≠ ≈ ≤ ≥ < > ∞ √ ∑ ∏ ∫ ∂ ∆ ∇ π ° ′ ″ ‰ % ¼ ½ ¾ ⅓ ⅔ ² ³ ⁿ ¹ ∈ ∉ ∩ ∪ ⊂ ⊃ ∀ ∃ ¬ ∧ ∨ "
                   "⇒ ⇔ ∴ ∵ ∝ ∠ ⊥ ∥ ∅ ℝ ℕ ℤ ℚ ℂ",
    "Letras griegas": "α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω Α Β Γ Δ Ε Ζ Η Θ Ι Κ Λ Μ Ν Ξ Ο Π Ρ Σ Τ Υ Φ Χ Ψ Ω",
    "Monedas": "€ £ ¥ ¢ $ ₡ ₩ ₹ ₽ ₪ ₦ ₱ ₫ ₲ ₿ ¤",
    "Puntuación y texto": "¿ ¡ « » “ ” ‘ ’ „ — – … • · § ¶ † ‡ © ® ™ ª º № ¦ ‹ ›",
    "Flechas": "← ↑ → ↓ ↔ ↕ ⇐ ⇑ ⇒ ⇓ ⇔ ↩ ↪ ➜ ➔ ↗ ↘ ↙ ↖",
    "Letras con tilde y otras": "á é í ó ú ü ñ Á É Í Ó Ú Ü Ñ à è ì ò ù â ê î ô û ä ë ï ö ç ã õ ß æ œ å ø",
    "Otros": "✓ ✔ ✗ ✘ ★ ☆ ♥ ♦ ♣ ♠ ☀ ☁ ☂ ☎ ✉ ✂ ☺ ☹ ♀ ♂ ⚠ ♪ ♫ ☑ ☐ ☒",
}


def symbols_of(group: str) -> list[str]:
    return SYMBOL_GROUPS[group].split()
