export interface PermissionDisplayCopy {
  title: string;
  description: string;
}

type ResourceCopy = {
  title: string;
  object: string;
  singular: string;
};

const RESOURCES: Record<string, ResourceCopy> = {
  "identity.organizations": { title: "Organizasyon", object: "organizasyonları", singular: "organizasyon" },
  "identity.users": { title: "Kullanıcı", object: "organizasyon kullanıcılarını", singular: "organizasyon kullanıcısı" },
  "identity.roles": { title: "Rol", object: "organizasyon rollerini", singular: "organizasyon rolü" },
  "identity.role_templates": { title: "Rol şablonu", object: "rol şablonlarını", singular: "rol şablonu" },
  "identity.permissions": { title: "İzin", object: "platform izinlerini", singular: "platform izni" },
  "fair_crm.activities": { title: "Aktivite", object: "aktiviteleri", singular: "aktivite" },
  "fair_crm.admin.backups": { title: "Veritabanı yedeği", object: "veritabanı yedeklerini", singular: "veritabanı yedeği" },
  "fair_crm.admin.data_operations": { title: "Veri işlemi", object: "veri işlemlerini", singular: "veri işlemi" },
  "fair_crm.contacts": { title: "İletişim kişisi", object: "iletişim kişilerini", singular: "iletişim kişisi" },
  "fair_crm.cost_catalog.categories": { title: "Maliyet kategorisi", object: "maliyet kategorilerini", singular: "maliyet kategorisi" },
  "fair_crm.cost_catalog.products": { title: "Maliyet ürünü", object: "maliyet ürünlerini", singular: "maliyet ürünü" },
  "fair_crm.customers": { title: "Müşteri", object: "müşterileri", singular: "müşteri" },
  "fair_crm.dashboard": { title: "Gösterge paneli", object: "gösterge panelini", singular: "gösterge paneli" },
  "fair_crm.email_accounts": { title: "E-posta hesabı", object: "e-posta hesaplarını", singular: "e-posta hesabı" },
  "fair_crm.fairs": { title: "Fuar", object: "fuarları", singular: "fuar" },
  "fair_crm.imports": { title: "Veri aktarımı", object: "veri aktarımlarını", singular: "veri aktarımı" },
  "fair_crm.mail_templates": { title: "E-posta şablonu", object: "e-posta şablonlarını", singular: "e-posta şablonu" },
  "fair_crm.fair_emails": { title: "Fuar e-postası", object: "fuar e-postalarını", singular: "fuar e-postası" },
  "fair_crm.quotes": { title: "Teklif", object: "teklifleri", singular: "teklif" },
  "fair_crm.quote_templates": { title: "Teklif şablonu", object: "teklif şablonlarını", singular: "teklif şablonu" },
  "fair_crm.operations": { title: "Operasyon", object: "operasyonları", singular: "operasyon" },
  "fair_crm.participations": { title: "Fuar katılımı", object: "fuar katılımlarını", singular: "fuar katılımı" },
  "fair_crm.scraper": { title: "Web veri toplama", object: "web veri toplama kayıtlarını", singular: "web veri toplama kaydı" },
  "fair_crm.template_contents": { title: "Şablon içeriği", object: "şablon içeriklerini", singular: "şablon içeriği" },
  "fair_crm.todos": { title: "Görev", object: "görevleri", singular: "görev" },
  "fair_crm.todos.outcomes": { title: "Görev sonucu", object: "görev sonuçlarını", singular: "görev sonucu" },
  "settings.platform": { title: "Platform ayarı", object: "organizasyon ayarlarını", singular: "organizasyon ayarı" },
  "jobs.platform": { title: "Arka plan işi", object: "arka plan işlerini", singular: "arka plan işi" },
  "notifications.platform": { title: "Bildirim", object: "organizasyon bildirimlerini", singular: "organizasyon bildirimi" },
  "audit.logs": { title: "Denetim kaydı", object: "organizasyon denetim kayıtlarını", singular: "denetim kaydı" },
};

const SPECIAL: Record<string, PermissionDisplayCopy> = {
  "identity.roles.assign": { title: "Rol atama", description: "Kullanıcılara organizasyon rolü atayabilir." },
  "identity.roles.assign_protected": { title: "Korunan rol atama", description: "Kullanıcılara korunan sistem rollerini atayabilir." },
  "identity.role_templates.manage": { title: "Rol şablonlarını yönetme", description: "Varsayılan rol şablonlarını oluşturabilir ve değiştirebilir." },
  "identity.permissions.lifecycle": { title: "İzin durumunu yönetme", description: "Platform izinlerini etkinleştirebilir, kilitleyebilir veya devre dışı bırakabilir." },
  "fair_crm.imports.execute": { title: "Veri aktarımını uygulama", description: "Hazırlanan veri aktarımını sisteme uygulayabilir." },
  "fair_crm.mail_templates.execute": { title: "E-posta şablonunu çalıştırma", description: "E-posta şablonunu işleyebilir, önizleyebilir ve test gönderimi yapabilir." },
  "fair_crm.fair_emails.execute": { title: "Fuar e-postası gönderme", description: "Fuar e-postalarını alıcılara gönderebilir." },
  "fair_crm.operations.execute": { title: "Operasyon çalıştırma", description: "Hazırlanmış operasyonları çalıştırabilir." },
  "fair_crm.scraper.execute": { title: "Web veri toplama işlemini çalıştırma", description: "Web veri toplama işlemlerini başlatabilir ve çalışma çıktısına erişebilir." },
  "jobs.platform.enqueue": { title: "Arka plan işi başlatma", description: "Organizasyon için yeni bir arka plan işi kuyruğa ekleyebilir." },
  "jobs.platform.read": { title: "Arka plan işi durumunu görüntüleme", description: "Arka plan işlerinin çalışma durumunu görüntüleyebilir." },
  "notifications.platform.send": { title: "Bildirim gönderme", description: "Organizasyon bildirimlerini gönderebilir." },
  "notifications.platform.read": { title: "Bildirim durumunu görüntüleme", description: "Bildirimlerin teslimat durumunu görüntüleyebilir." },
  "settings.platform.read": { title: "Organizasyon ayarlarını görüntüleme", description: "Organizasyon ayarlarını görüntüleyebilir." },
  "settings.platform.update": { title: "Organizasyon ayarlarını düzenleme", description: "Organizasyon ayarlarını değiştirebilir." },
  "audit.logs.read": { title: "Denetim kayıtlarını görüntüleme", description: "Organizasyondaki denetim ve işlem kayıtlarını görüntüleyebilir." },
};

const ACTIONS: Record<string, { title: string; describe: (resource: ResourceCopy) => string }> = {
  read: { title: "görüntüleme", describe: (resource) => `${capitalize(resource.object)} görüntüleyebilir.` },
  create: { title: "oluşturma", describe: (resource) => `Yeni ${resource.singular} oluşturabilir.` },
  update: { title: "düzenleme", describe: (resource) => `${capitalize(resource.object)} düzenleyebilir.` },
  delete: { title: "silme", describe: (resource) => `${capitalize(resource.object)} silebilir.` },
  download: { title: "indirme", describe: (resource) => `${capitalize(resource.object)} indirebilir.` },
  preview: { title: "önizleme", describe: (resource) => `${capitalize(resource.object)} önizleyebilir.` },
  send: { title: "gönderme", describe: (resource) => `${capitalize(resource.object)} gönderebilir.` },
  run: { title: "çalıştırma", describe: (resource) => `${capitalize(resource.object)} çalıştırabilir.` },
  execute: { title: "çalıştırma", describe: (resource) => `${capitalize(resource.object)} çalıştırabilir.` },
};

function capitalize(value: string): string {
  return value.length ? value[0].toLocaleUpperCase("tr-TR") + value.slice(1) : value;
}

function resolveResource(code: string): [string, ResourceCopy] | undefined {
  return Object.entries(RESOURCES)
    .sort(([left], [right]) => right.length - left.length)
    .find(([prefix]) => code === prefix || code.startsWith(`${prefix}.`));
}

export function getPermissionDisplayCopy(code: string): PermissionDisplayCopy | undefined {
  const special = SPECIAL[code];
  if (special) return special;

  const resolved = resolveResource(code);
  if (!resolved) return undefined;
  const [prefix, resource] = resolved;
  const action = code.slice(prefix.length + 1);
  const actionCopy = ACTIONS[action];
  if (!actionCopy) return undefined;

  return {
    title: `${resource.title} ${actionCopy.title}`,
    description: actionCopy.describe(resource),
  };
}

export function formatPermissionDescription(code: string, fallback: string): string {
  const copy = getPermissionDisplayCopy(code);
  return copy ? `${copy.title} — ${copy.description}` : fallback;
}
