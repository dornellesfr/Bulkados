export function CardTitle({
  namePt,
  nameEn,
}: {
  namePt: string | null
  nameEn: string
}) {
  return (
    <div className="min-w-0">
      <p className="font-medium">{namePt ?? nameEn}</p>
      {namePt ? (
        <p className="text-sm text-muted-foreground">{nameEn}</p>
      ) : null}
    </div>
  )
}
