import {
  PRODUCT_OF_LINE,
  SUPPORT_EMAIL,
  registeredAddress,
  grievanceOfficer,
} from "@/data/legal";

/**
 * "FounderConsole is a product of ULTRASAFE AI INDIA PRIVATE LIMITED" plus the
 * registered office, when the owner has filled it in (client/src/data/legal.ts).
 * A TODO placeholder renders nothing, never a fake address.
 */
export function LegalEntityNotice({ className = "", showEmail = true }: { className?: string; showEmail?: boolean }) {
  const address = registeredAddress();
  return (
    <div className={className} data-testid="legal-entity-notice">
      <p>{PRODUCT_OF_LINE}</p>
      {address && <p data-testid="legal-entity-address">Registered office: {address}</p>}
      {showEmail && (
        <p>
          Email:{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-400 hover:underline">
            {SUPPORT_EMAIL}
          </a>
        </p>
      )}
    </div>
  );
}

/** Grievance Officer paragraph (Indian IT Rules, 2021). Name only once filled in. */
export function GrievanceOfficerText() {
  const officer = grievanceOfficer();
  return (
    <p data-testid="grievance-officer">
      In accordance with the Information Technology Act, 2000 and the rules made under it, complaints about
      content or the processing of your information can be sent to our Grievance Officer
      {officer.name ? `, ${officer.name}` : ""}, at{" "}
      <a href={`mailto:${officer.email}`} className="text-indigo-400 hover:underline">
        {officer.email}
      </a>
      . We acknowledge complaints within 24 hours and resolve them within 15 days of receipt.
    </p>
  );
}
