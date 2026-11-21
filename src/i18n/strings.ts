export type Locale = 'ar';

export interface AppStrings {
  title: string;
  subtitle: string;
  difficultyLabel: string;
  difficulties: {
    easy: string;
    normal: string;
    hard: string;
  };
  stats: {
    attempts: string;
    time: string;
    pairs: string;
    secondsUnit: string;
  };
  actions: {
    newGame: string;
    playAgain: string;
    submitScore: string;
    submittingScore: string;
  };
  endScreen: {
    congratsTitle: string;
    congratsSubtitle: string;
    playerNameLabel: string;
    playerNamePlaceholder: string;
    scoreSentSuccess: string;
    scoreSentError: string;
  };
  card: {
    hiddenLabel: string;
    matchedLabel: string;
  };
}

export const STRINGS: Record<Locale, AppStrings> = {
  ar: {
    title: 'تطابق البطاقات',
    subtitle: 'اقلب البطاقات واعثر على جميع الأزواج المتطابقة',
    difficultyLabel: 'مستوى الصعوبة',
    difficulties: {
      easy: 'سهل (4×3)',
      normal: 'عادي (4×4)',
      hard: 'صعب (6×4)',
    },
    stats: {
      attempts: 'المحاولات',
      time: 'الوقت',
      pairs: 'الأزواج',
      secondsUnit: 'ث',
    },
    actions: {
      newGame: 'لعبة جديدة',
      playAgain: 'العب مرة أخرى',
      submitScore: 'حفظ النتيجة',
      submittingScore: 'جاري الإرسال...',
    },
    endScreen: {
      congratsTitle: 'أحسنت! لقد أنهيت اللعبة',
      congratsSubtitle: 'تمت مطابقة جميع الأزواج بنجاح.',
      playerNameLabel: 'اسم اللاعب',
      playerNamePlaceholder: 'أدخل اسمك (اختياري)',
      scoreSentSuccess: 'تم إرسال النتيجة بنجاح!',
      scoreSentError: 'تعذّر الاتصال بالخادم لحفظ النتيجة، يمكنك المتابعة واللعب مجددًا.',
    },
    card: {
      hiddenLabel: 'بطاقة مقلوبة',
      matchedLabel: 'بطاقة متطابقة',
    },
  },
};

export function getStrings(locale: Locale = 'ar'): AppStrings {
  return STRINGS[locale];
}
