"use strict";

const {HttpsError} = require(
    "firebase-functions/v2/https",
);

const {assertAuth} = require("../call_util");

/**
 * Requires an authenticated callable request.
 *
 * @param {object} request Callable request.
 * @return {string} Firebase user ID.
 */
function requireAuthenticatedUser(request) {
  return assertAuth(request);
}

/**
 * Requires an allowed administrative role.
 *
 * @param {object} request Callable request.
 * @param {string[]} allowedRoles Allowed roles.
 * @return {object} Authenticated administrator information.
 */
function requireAdminRole(
    request,
    allowedRoles = ["super_admin"],
) {
  const uid = assertAuth(request);
  const token = request.auth &&
      request.auth.token ?
      request.auth.token :
      {};

  const role = String(
      token.role ||
      token.adminRole ||
      "",
  ).trim().toLowerCase();

  if (!allowedRoles.includes(role)) {
    throw new HttpsError(
        "permission-denied",
        "Administrative permission required",
    );
  }

  return {
    uid,
    role,
  };
}

module.exports = {
  requireAuthenticatedUser,
  requireAdminRole,
};
