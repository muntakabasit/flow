import Foundation

enum FlowStrings {
    enum Lang {
        case en
        case pt
    }

    static func trustBar(_ lang: Lang) -> String {
        switch lang {
        case .en: return "Live · English ↔ Português (Brasil)"
        case .pt: return "Ao vivo · Português (Brasil) ↔ English"
        }
    }

    static func wordmark() -> String { "F L O W" }
    static func subtitle(_ lang: Lang) -> String {
        switch lang {
        case .en: return "“DIASPORA INTERPRETER”"
        case .pt: return "“INTÉRPRETE DA DIÁSPORA”"
        }
    }

    static func holdToSpeak(_ lang: Lang) -> String {
        switch lang {
        case .en: return "HOLD TO SPEAK"
        case .pt: return "SEGURE PARA FALAR"
        }
    }

    static func listening(_ lang: Lang) -> String {
        switch lang {
        case .en: return "LISTENING…"
        case .pt: return "OUVINDO…"
        }
    }

    static func translating(_ lang: Lang) -> String {
        switch lang {
        case .en: return "TRANSLATING…"
        case .pt: return "TRADUZINDO…"
        }
    }

    static func youSaid(_ lang: Lang) -> String {
        switch lang {
        case .en: return "YOU SAID"
        case .pt: return "VOCÊ DISSE"
        }
    }

    static func theyHeard(_ lang: Lang) -> String {
        switch lang {
        case .en: return "THEY HEARD"
        case .pt: return "ELES OUVIRAM"
        }
    }

    static func microcopy(_ lang: Lang) -> String {
        switch lang {
        case .en: return "YOUR ACCENT BELONGS HERE.\nSPEAK AS YOU ARE. FLOW ADAPTS."
        case .pt: return "SEU SOTAQUE PERTENCE AQUI.\nFALE COMO VOCÊ É. O FLOW SE ADAPTA."
        }
    }

    static func speakNaturally(_ lang: Lang) -> String {
        switch lang {
        case .en: return "Speak naturally…"
        case .pt: return "Fale naturalmente…"
        }
    }

    static func tapToContinue(_ lang: Lang) -> String {
        switch lang {
        case .en: return "TAP OR HOLD TO CONTINUE"
        case .pt: return "TOQUE OU SEGURE PARA CONTINUAR"
        }
    }

    static func sampleTurns() -> [FlowSession.Turn] {
        return [
            .init(sourceText: "So today is Sunday and I'm trying to figure this out.",
                  sourceLang: "EN",
                  targetText: "Então hoje é domingo e estou tentando entender isso.",
                  targetLang: "PT-BR"),
            .init(sourceText: "We need this to work properly on mobile devices.",
                  sourceLang: "EN",
                  targetText: "Precisamos que isso funcione bem em dispositivos móveis.",
                  targetLang: "PT-BR"),
            .init(sourceText: "The translation panel should show multiple turns.",
                  sourceLang: "EN",
                  targetText: "O painel de tradução deve mostrar várias falas.",
                  targetLang: "PT-BR"),
        ]
    }
}
