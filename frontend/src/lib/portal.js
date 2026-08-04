export const ADMIN_ROLES = [
  "super_admin",
  "moderator",
  "support_agent",
  "finance_admin",
  "verification_agent",
];

export const HR_ROLES = [
  "hr_admin",
  "hr_manager",
  "payroll_admin",
];

export const EMPLOYEE_ROLES = ["employee"];

export function portalForRole(role) {
  if (HR_ROLES.includes(role)) return "hr";
  if (EMPLOYEE_ROLES.includes(role)) return "employee";
  return "admin";
}

export function homeForRole(role) {
  const portal = portalForRole(role);
  if (portal === "hr") return "/hr";
  if (portal === "employee") return "/employee";
  return "/admin";
}

export function roleCanSeeItem(role, item) {
  if (item.superAdminOnly && role !== "super_admin") return false;
  if (item.roles && !item.roles.includes(role)) return false;
  return true;
}
