#!/usr/bin/swift
// secrets-keychain-add.swift — Add a generic password to macOS Keychain.
// Usage: echo -n "$VALUE" | ./secrets-keychain-add.swift <service> [--icloud] [--update]
// Value is read from stdin (never argv — argv is visible via `ps`).
// Exit codes: 0 ok · 1 usage/mac-only · 2 keychain error · 3 duplicate (w/o --update)

import Foundation
import Security

let argv = CommandLine.arguments
guard argv.count >= 2 else {
    FileHandle.standardError.write("usage: echo -n VALUE | secrets-keychain-add.swift <service> [--icloud] [--update]\n".data(using: .utf8)!)
    exit(1)
}
let service = argv[1]
let icloud  = argv.contains("--icloud")
let update  = argv.contains("--update")

// Read value from stdin as raw bytes — preserves whatever token format exactly
let valueData = FileHandle.standardInput.readDataToEndOfFile()
if valueData.isEmpty {
    FileHandle.standardError.write("error: empty stdin (nothing to store)\n".data(using: .utf8)!)
    exit(1)
}

var query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: "nous",
    kSecValueData as String: valueData,
    kSecAttrSynchronizable as String: icloud ? kCFBooleanTrue! : kCFBooleanFalse!
]

var status = SecItemAdd(query as CFDictionary, nil)

if status == errSecDuplicateItem {
    if update {
        let search: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: "nous",
            kSecAttrSynchronizable as String: icloud ? kCFBooleanTrue! : kCFBooleanFalse!
        ]
        status = SecItemUpdate(search as CFDictionary,
                               [kSecValueData as String: valueData] as CFDictionary)
    } else {
        FileHandle.standardError.write("error: item already exists; pass --update to replace\n".data(using: .utf8)!)
        exit(3)
    }
}

if status != errSecSuccess {
    FileHandle.standardError.write("error: keychain status \(status)\n".data(using: .utf8)!)
    exit(2)
}

exit(0)
