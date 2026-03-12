import SwiftUI

struct DatabaseTableList: View {
    @Bindable var dbManager: DatabaseManager
    var tables: [TeenybaseTable]

    var body: some View {
        List(tables, selection: $dbManager.selectedTable) { table in
            HStack(spacing: 8) {
                Image(systemName: "tablecells")
                    .foregroundStyle(.secondary)
                    .frame(width: 16)
                VStack(alignment: .leading, spacing: 2) {
                    Text(table.name)
                        .font(.system(.body, design: .monospaced))
                    Text("\(table.fields.count) fields")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
                Spacer()
            }
            .tag(table)
            .contentShape(Rectangle())
        }
        .listStyle(.sidebar)
    }
}
