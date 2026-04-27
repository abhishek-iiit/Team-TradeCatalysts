export default function ContactCard({ contact }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-gray-900 text-sm">
            {contact.first_name} {contact.last_name}
            {contact.is_primary && (
              <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-medium">
                Primary
              </span>
            )}
          </p>
          {contact.designation && (
            <p className="text-xs text-gray-500">{contact.designation}</p>
          )}
        </div>
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
          {contact.source}
        </span>
      </div>

      <div className="space-y-1">
        {contact.email ? (
          <a
            href={`mailto:${contact.email}`}
            className="flex items-center gap-2 text-xs text-indigo-600 hover:underline"
          >
            <span className="w-4 text-center">✉</span>
            {contact.email}
          </a>
        ) : (
          <p className="text-xs text-gray-400 italic">No email</p>
        )}
        {contact.phone ? (
          <a
            href={`tel:${contact.phone}`}
            className="flex items-center gap-2 text-xs text-gray-700 hover:underline"
          >
            <span className="w-4 text-center">📞</span>
            {contact.phone}
          </a>
        ) : (
          <p className="text-xs text-gray-400 italic">No phone</p>
        )}
        {contact.linkedin_url && (
          <a
            href={contact.linkedin_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 text-xs text-blue-600 hover:underline"
          >
            <span className="w-4 text-center">in</span>
            LinkedIn
          </a>
        )}
      </div>
    </div>
  )
}
