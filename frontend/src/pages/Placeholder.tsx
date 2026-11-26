import { useLocale } from '../hooks/useLocale';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

/**
 * Empty state for pages not implemented in this phase.
 * Shows a clear "not implemented" message — never fake data.
 */
export function Placeholder({ titleKey }: { titleKey?: string }) {
  const { t } = useLocale();
  const title = titleKey ? t(titleKey) : t('placeholder.title');

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{t('placeholder.description')}</p>
        <p className="mt-2 text-sm" role="status">
          {t('common.empty')}
        </p>
      </CardContent>
    </Card>
  );
}
