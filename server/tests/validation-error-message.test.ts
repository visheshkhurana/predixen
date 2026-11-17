// FastAPI 422s must reach the founder as a sentence, not "Request failed (422)".
import assert from "assert";
import { validationDetailMessage } from "../../client/src/lib/errors";

assert.equal(
  validationDetailMessage([{ loc: ["body", "email"], msg: "value is not a valid email address: The part after the @-sign is a special-use or reserved name that cannot be used with email." }]),
  "Please use a real email address you can receive mail at.",
);
assert.equal(
  validationDetailMessage([{ loc: ["body", "password"], msg: "Value error, Password must contain a number" }]),
  "Password: Password must contain a number",
);
assert.equal(
  validationDetailMessage([{ loc: ["body", "monthly_revenue"], msg: "Input should be a valid number" }]),
  "Monthly revenue: Input should be a valid number",
);
assert.equal(validationDetailMessage("Company not found"), null);
assert.equal(validationDetailMessage({ message: "x" }), null);
assert.equal(validationDetailMessage([]), null);
console.log("validation-error-message: ok");
