import SwiftUI

struct DatabaseRecordEditor: View {
    let fields: [TeenybaseField]
    let existingRow: TableRow?
    let onSave: ([String: Any]) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var fieldValues: [String: String] = [:]

    private var isEditing: Bool { existingRow != nil }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text(isEditing ? "Edit Record" : "New Record")
                    .font(.headline)
                Spacer()
                Button("Cancel") { dismiss() }
                    .keyboardShortcut(.cancelAction)
                Button(isEditing ? "Save" : "Create") { save() }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
            }
            .padding()

            Divider()

            // Fields form
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(editableFields) { field in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(spacing: 4) {
                                Text(field.name)
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                if let type = field.type {
                                    Text(type)
                                        .font(.caption2)
                                        .foregroundStyle(.tertiary)
                                        .padding(.horizontal, 4)
                                        .padding(.vertical, 1)
                                        .background(.quaternary, in: RoundedRectangle(cornerRadius: 3))
                                }
                                if field.notNull == true {
                                    Text("required")
                                        .font(.caption2)
                                        .foregroundStyle(.orange)
                                }
                            }
                            TextField("", text: binding(for: field.name))
                                .textFieldStyle(.roundedBorder)
                                .font(.system(.body, design: .monospaced))
                        }
                    }
                }
                .padding()
            }
        }
        .frame(width: 480, height: 500)
        .onAppear { populateValues() }
    }

    private var editableFields: [TeenybaseField] {
        fields.filter { field in
            // Skip auto-generated fields when creating
            if !isEditing {
                if field.primary == true && field.autoIncrement == true { return false }
                if field.name == "created_at" || field.name == "updated_at" { return false }
            }
            return true
        }
    }

    private func binding(for key: String) -> Binding<String> {
        Binding(
            get: { fieldValues[key, default: ""] },
            set: { fieldValues[key] = $0 }
        )
    }

    private func populateValues() {
        guard let row = existingRow else { return }
        for (key, value) in row {
            if case .null = value { continue }
            fieldValues[key] = value.description
        }
    }

    private func save() {
        var values: [String: Any] = [:]
        for field in editableFields {
            guard let raw = fieldValues[field.name], !raw.isEmpty else { continue }
            values[field.name] = coerce(raw, type: field.type ?? "text")
        }
        onSave(values)
        dismiss()
    }

    private func coerce(_ value: String, type: String) -> Any {
        switch type {
        case "number", "integer":
            if let intVal = Int(value) { return intVal }
            if let dblVal = Double(value) { return dblVal }
            return value
        case "bool":
            return value.lowercased() == "true" || value == "1"
        default:
            return value
        }
    }
}
