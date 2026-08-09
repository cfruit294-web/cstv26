const ROLE_LABELS: Record<string, string> = {
  admin: "Administrateur",
  moderator: "Modérateur",
  creator: "Créateur",
  user: "Utilisateur",
  business: "Entreprise",
  support: "Support",
};

export default function RoleBarChart({ byRole }: { byRole: Record<string, number> }) {
  const entries = Object.entries(byRole).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, count]) => count));

  if (entries.length === 0) return null;

  return (
    <div className="rounded-lg bg-surface p-4 ring-1 ring-white/5">
      <p className="mb-4 text-sm font-medium text-foreground">Utilisateurs par rôle</p>
      <div className="space-y-3">
        {entries.map(([role, count]) => (
          <div key={role} className="flex items-center gap-3">
            <span className="w-28 shrink-0 truncate text-xs text-muted">{ROLE_LABELS[role] ?? role}</span>
            <div className="h-4 flex-1 rounded-r-[4px] bg-surface-2">
              <div
                className="h-4 rounded-r-[4px] bg-accent"
                style={{ width: `${Math.max((count / max) * 100, 4)}%` }}
                title={`${ROLE_LABELS[role] ?? role} : ${count}`}
              />
            </div>
            <span className="w-10 shrink-0 text-right text-xs text-muted">
              {new Intl.NumberFormat("fr-FR").format(count)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
