import { Card, PageHeader } from "../components";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="page-section">
      <PageHeader title={title} subtitle="이 화면은 다음 단계에서 상세 위젯이 추가될 예정입니다." />
      <Card>
        <p>Placeholder page for {title}.</p>
      </Card>
    </div>
  );
}
