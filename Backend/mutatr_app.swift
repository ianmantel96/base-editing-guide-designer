import AppKit
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, NSWindowDelegate, WKScriptMessageHandler {
    var window: NSWindow!
    var webView: WKWebView!
    var lastFindQuery = ""

    let backendDir: URL = {
        let executableURL = URL(fileURLWithPath: CommandLine.arguments[0]).resolvingSymlinksInPath()
        let appBundleURL = executableURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        return appBundleURL.deletingLastPathComponent().appendingPathComponent("Backend", isDirectory: true)
    }()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        createMenu()
        createWindow()
        startMutatr()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag {
            window.makeKeyAndOrderFront(nil)
        }
        NSApp.activate(ignoringOtherApps: true)
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        _ = runPython(arguments: ["mutatr_runner.py", "stop"])
    }

    private func createMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu()
        appMenuItem.submenu = appMenu
        let aboutItem = NSMenuItem(title: "About MUTATR", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        aboutItem.target = NSApp
        appMenu.addItem(aboutItem)
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit MUTATR", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenuItem.submenu = editMenu
        let findItem = NSMenuItem(title: "Find In Page…", action: #selector(showFindPrompt(_:)), keyEquivalent: "f")
        findItem.keyEquivalentModifierMask = [.command]
        findItem.target = self
        editMenu.addItem(findItem)

        NSApp.mainMenu = mainMenu
    }

    private func createWindow() {
        let rect = NSRect(x: 0, y: 0, width: 1380, height: 920)
        window = NSWindow(
            contentRect: rect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.center()
        window.title = "MUTATR"
        window.setFrameAutosaveName("MUTATRMainWindow")
        window.delegate = self

        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "mutatrSaveFile")
        config.userContentController.add(self, name: "mutatrSaveFolder")
        webView = WKWebView(frame: rect, configuration: config)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.setValue(false, forKey: "drawsBackground")
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func startMutatr() {
        window.title = "MUTATR - Starting"
        let start = runPython(arguments: ["mutatr_runner.py", "start", "--no-open"])
        if start.status != 0 {
            presentError("MUTATR could not start.", detail: start.stderr.isEmpty ? start.stdout : start.stderr)
            return
        }
        loadCurrentUrl()
    }

    private func loadCurrentUrl() {
        let status = runPython(arguments: ["mutatr_runner.py", "status"])
        guard status.status == 0, let data = status.stdout.data(using: .utf8) else {
            presentError("MUTATR could not read its runtime status.", detail: status.stderr.isEmpty ? status.stdout : status.stderr)
            return
        }
        do {
            let parsed = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            let app = parsed?["app"] as? [String: Any]
            guard let urlText = app?["url"] as? String, !urlText.isEmpty, let url = URL(string: urlText) else {
                presentError("MUTATR started, but no app URL was available.", detail: status.stdout)
                return
            }
            window.title = "MUTATR"
            webView.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))
        } catch {
            presentError("MUTATR could not parse its runtime status.", detail: error.localizedDescription)
        }
    }

    private func presentError(_ title: String, detail: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = detail
        alert.alertStyle = .critical
        alert.runModal()
    }

    private func runPython(arguments: [String]) -> (status: Int32, stdout: String, stderr: String) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = arguments
        process.currentDirectoryURL = backendDir

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return (1, "", "Failed to run Python: \(error.localizedDescription)")
        }

        let stdout = String(data: stdoutPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: stderrPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return (process.terminationStatus, stdout, stderr)
    }

    private func isLocalAppUrl(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return host == "127.0.0.1" || host == "localhost"
    }

    private func isIgnorablePlaceholderUrl(_ url: URL) -> Bool {
        let absolute = url.absoluteString.lowercased()
        return absolute == "about:blank" || absolute.hasPrefix("javascript:") || absolute.hasPrefix("blob:")
    }

    private func openExternally(_ url: URL) {
        NSWorkspace.shared.open(url)
    }

    private func decodeBase64(_ text: String) -> Data? {
        Data(base64Encoded: text)
    }

    private func saveFile(name: String, data: Data) -> Bool {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = name
        panel.canCreateDirectories = true
        if panel.runModal() == .OK, let url = panel.url {
            do {
                try data.write(to: url)
                return true
            } catch {
                presentError("MUTATR could not save the file.", detail: error.localizedDescription)
                return false
            }
        }
        return false
    }

    private func saveFilesToFolder(rootName: String, files: [(String, Data)]) -> Bool {
        let panel = NSOpenPanel()
        panel.message = "Choose a folder for the MUTATR export bundle."
        panel.prompt = "Choose Folder"
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = true

        if panel.runModal() == .OK, let root = panel.url {
            let projectDir = root.appendingPathComponent(rootName, isDirectory: true)
            do {
                try FileManager.default.createDirectory(at: projectDir, withIntermediateDirectories: true)
                for (name, data) in files {
                    try data.write(to: projectDir.appendingPathComponent(name))
                }
                return true
            } catch {
                presentError("MUTATR could not save the export folder.", detail: error.localizedDescription)
                return false
            }
        }
        return false
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "mutatrSaveFile" {
            guard
                let body = message.body as? [String: Any],
                let name = body["name"] as? String,
                let base64 = body["base64"] as? String,
                let data = decodeBase64(base64)
            else {
                return
            }
            let saved = saveFile(name: name, data: data)
            let js = "window.__mutatrNativeSaveComplete && window.__mutatrNativeSaveComplete(\(saved ? "true" : "false"));"
            webView.evaluateJavaScript(js)
            return
        }

        if message.name == "mutatrSaveFolder" {
            guard
                let body = message.body as? [String: Any],
                let rootName = body["rootName"] as? String,
                let fileEntries = body["files"] as? [[String: Any]]
            else {
                return
            }

            var files: [(String, Data)] = []
            for entry in fileEntries {
                guard
                    let name = entry["name"] as? String,
                    let base64 = entry["base64"] as? String,
                    let data = decodeBase64(base64)
                else {
                    continue
                }
                files.append((name, data))
            }

            let saved = saveFilesToFolder(rootName: rootName, files: files)
            let js = "window.__mutatrNativeFolderSaveComplete && window.__mutatrNativeFolderSaveComplete(\(saved ? "true" : "false"));"
            webView.evaluateJavaScript(js)
        }
    }

    private func runFind(query: String) {
        let escaped = query
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .replacingOccurrences(of: "\n", with: "\\n")
        webView.evaluateJavaScript("window.find(\"\(escaped)\", false, false, true, false, true, false);")
    }

    @objc private func showFindPrompt(_ sender: Any?) {
        let alert = NSAlert()
        alert.messageText = "Find In Page"
        alert.informativeText = "Search the text currently visible inside MUTATR."
        alert.alertStyle = .informational
        alert.addButton(withTitle: "Find")
        alert.addButton(withTitle: "Cancel")

        let input = NSTextField(frame: NSRect(x: 0, y: 0, width: 280, height: 24))
        input.stringValue = lastFindQuery
        alert.accessoryView = input

        let response = alert.runModal()
        guard response == .alertFirstButtonReturn else { return }
        let query = input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return }
        lastFindQuery = query
        runFind(query: query)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }

        if isIgnorablePlaceholderUrl(url) {
            decisionHandler(.cancel)
            return
        }

        if navigationAction.targetFrame == nil {
            if isLocalAppUrl(url) {
                webView.load(URLRequest(url: url))
            } else {
                openExternally(url)
            }
            decisionHandler(.cancel)
            return
        }

        if !isLocalAppUrl(url) {
            openExternally(url)
            decisionHandler(.cancel)
            return
        }

        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url {
            if isIgnorablePlaceholderUrl(url) {
                return nil
            }
            if isLocalAppUrl(url) {
                webView.load(URLRequest(url: url))
            } else {
                openExternally(url)
            }
        }
        return nil
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
