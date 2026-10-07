package ai.nova.app

import android.graphics.Color
import android.os.Bundle
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import android.view.View
import android.view.Gravity
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private val prefs by lazy { getSharedPreferences("nova", MODE_PRIVATE) }
    private lateinit var endpoint: EditText
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var message: EditText
    private lateinit var status: TextView
    private lateinit var progress: TextView
    private lateinit var messages: LinearLayout
    private lateinit var sendButton: Button
    private lateinit var attachButton: Button
    private val attachments = mutableListOf<JSONObject>()
    private var projectId: String? = null
    private val filePickerCode = 7001
    private lateinit var authButton: Button
    private lateinit var modelSpinner: Spinner
    private lateinit var conversationSpinner: Spinner
    private lateinit var newChatButton: Button
    private val conversations = mutableListOf<JSONObject>()
    private var conversationId: String? = null
    private var loadingConversation = false
    private val history = mutableListOf<JSONObject>()
    private var streaming = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (prefs.getString("token", null) != null) showChat()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(15, 15, 18))
            setPadding(20, 20, 20, 16)
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val title = TextView(this).apply {
            text = "NOVA"
            textSize = 28f
            setTextColor(Color.WHITE)
        }
        status = TextView(this).apply {
            text = "Offline"
            textSize = 13f
            setTextColor(Color.LTGRAY)
            gravity = Gravity.END
        }
        header.addView(title, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(status)

        progress = TextView(this).apply {
            text = ""
            textSize = 12f
            setTextColor(Color.LTGRAY)
            setPadding(4, 4, 4, 8)
            visibility = View.GONE
        }

        endpoint = field("API base URL", prefs.getString("api", "http://10.0.2.2:8000"))
        email = field("Email", prefs.getString("email", ""))
        password = field("Password", "")
        password.inputType = 129
        authButton = Button(this).apply { text = "Sign In / Create Account" }
        val chatBar = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        conversationSpinner = Spinner(this)
        newChatButton = Button(this).apply { text = "New Chat" }
        chatBar.addView(conversationSpinner, LinearLayout.LayoutParams(0, -2, 1f))
        chatBar.addView(newChatButton, LinearLayout.LayoutParams(-2, -2))

        modelSpinner = Spinner(this)

        messages = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val scroll = ScrollView(this).apply { addView(messages) }

        message = EditText(this).apply {
            hint = "Message NOVA..."
            minLines = 2
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            setBackgroundColor(Color.rgb(30, 30, 35))
            isEnabled = false
        }
        sendButton = Button(this).apply {
            text = "Send"
            isEnabled = false
        }
        val composer = LinearLayout(this).apply {
            gravity = Gravity.BOTTOM
            addView(message, LinearLayout.LayoutParams(0, -2, 1f))
            attachButton = Button(this@MainActivity).apply { text = "＋ File"; isEnabled = false }
            addView(attachButton, LinearLayout.LayoutParams(-2, -2))
            addView(sendButton, LinearLayout.LayoutParams(-2, -2))
        }

        root.addView(header)
        root.addView(progress)
        root.addView(endpoint)
        root.addView(email)
        root.addView(password)
        root.addView(authButton)
        root.addView(chatBar)
        root.addView(modelSpinner)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(composer)
        setContentView(root)

        authButton.setOnClickListener { authenticate() }
        sendButton.setOnClickListener { sendMessage() }
        attachButton.setOnClickListener { pickFile() }
        newChatButton.setOnClickListener { newChat() }
        conversationSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (!loadingConversation && position in conversations.indices) {
                    openConversation(conversations[position].optString("id"))
                }
            }
        }
    }

    private fun field(hintText: String, value: String?): EditText = EditText(this).apply {
        hint = hintText
        setText(value ?: "")
        singleLine = true
        setTextColor(Color.WHITE)
        setHintTextColor(Color.GRAY)
    }

    private fun bubble(text: String, user: Boolean): TextView {
        val view = TextView(this).apply {
            this.text = text
            textSize = 16f
            setTextColor(Color.WHITE)
            setPadding(18, 14, 18, 14)
            setBackgroundColor(if (user) Color.rgb(45, 45, 55) else Color.rgb(28, 42, 36))
        }
        val params = LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, 8, 0, 8) }
        messages.addView(view, params)
        return view
    }

    private fun authenticate() {
        val base = endpoint.text.toString().trim().trimEnd('/')
        val userEmail = email.text.toString().trim()
        val userPassword = password.text.toString()
        if (base.isBlank() || userEmail.isBlank() || userPassword.length < 8) {
            status.text = "Enter URL, email and 8+ character password"
            return
        }
        prefs.edit().putString("api", base).putString("email", userEmail).apply()
        authButton.isEnabled = false
        status.text = "Signing in..."
        thread {
            val login = request("POST", "$base/api/auth/login",
                JSONObject().put("email", userEmail).put("password", userPassword))
            if (login.code == 401 || login.code == 404) {
                val register = request("POST", "$base/api/auth/register",
                    JSONObject().put("email", userEmail).put("password", userPassword))
                if (register.code in 200..299) {
                    finishLogin(request("POST", "$base/api/auth/login",
                        JSONObject().put("email", userEmail).put("password", userPassword)))
                } else runOnUiThread { authError("Account creation failed: " + register.body) }
            } else finishLogin(login)
        }
    }

    private fun finishLogin(result: HttpResult) {
        if (result.code !in 200..299) {
            runOnUiThread { authError("Authentication failed: " + result.body) }
            return
        }
        try {
            val token = JSONObject(result.body).getString("access_token")
            prefs.edit().putString("token", token).apply()
            runOnUiThread { showChat() }
        } catch (_: Exception) {
            runOnUiThread { authError("Invalid login response") }
        }
    }

    private fun showChat() {
        endpoint.visibility = View.GONE
        email.visibility = View.GONE
        password.visibility = View.GONE
        authButton.visibility = View.GONE
        message.isEnabled = true
        sendButton.isEnabled = true
        newChatButton.isEnabled = true
        status.text = "● Ready"
        modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, arrayOf("Auto"))
        loadModels()
        loadProject()
        loadConversations()
        if (messages.childCount == 0) bubble("I'm NOVA. Ask me anything.", false)
    }

    private fun loadModels() {
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        thread {
            val result = request("GET", "$base/api/models")
            if (result.code in 200..299) {
                try {
                    val a = JSONArray(result.body)
                    val names = mutableListOf("Auto")
                    for (i in 0 until a.length()) {
                        val id = a.getJSONObject(i).optString("id")
                        if (id.isNotBlank()) names.add(id)
                    }
                    runOnUiThread {
                        modelSpinner.adapter = ArrayAdapter(
                            this, android.R.layout.simple_spinner_dropdown_item, names.distinct()
                        )
                    }
                } catch (_: Exception) {}
            }
        }
    }

    private fun loadConversations() {
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        thread {
            val result = request("GET", "$base/api/conversations", auth = authHeader())
            if (result.code == 401) {
                expireSession()
                return@thread
            }
            if (result.code in 200..299) {
                try {
                    val array = JSONArray(result.body)
                    val loaded = mutableListOf<JSONObject>()
                    for (i in 0 until array.length()) loaded.add(array.getJSONObject(i))
                    runOnUiThread {
                        conversations.clear()
                        conversations.addAll(loaded)
                        loadingConversation = true
                        conversationSpinner.adapter = ArrayAdapter(
                            this, android.R.layout.simple_spinner_dropdown_item,
                            conversations.map { it.optString("title", "Chat") }
                        )
                        loadingConversation = false
                        if (conversations.isNotEmpty()) openConversation(conversations[0].optString("id"))
                    }
                } catch (_: Exception) {}
            }
        }
    }

    private fun newChat() {
        if (streaming) return
        conversationId = null
        history.clear()
        attachments.clear()
        messages.removeAllViews()
        bubble("New conversation. Ask NOVA anything.", false)
        status.text = "● New chat"
    }

    private fun openConversation(id: String) {
        if (id.isBlank() || streaming) return
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        status.text = "Loading chat..."
        thread {
            val result = request("GET", "$base/api/conversations/$id", auth = authHeader())
            if (result.code == 401) {
                expireSession()
                return@thread
            }
            if (result.code !in 200..299) {
                runOnUiThread { status.text = "Could not load chat" }
                return@thread
            }
            try {
                val conversation = JSONObject(result.body)
                val restored = mutableListOf<JSONObject>()
                val msgs = conversation.optJSONArray("messages") ?: JSONArray()
                for (i in 0 until msgs.length()) {
                    val item = msgs.getJSONObject(i)
                    val role = item.optString("role")
                    val content = item.optString("content")
                    if ((role == "user" || role == "assistant") && content.isNotBlank()) {
                        restored.add(JSONObject().put("role", role).put("content", content))
                    }
                }
                runOnUiThread {
                    conversationId = conversation.optString("id")
                    history.clear()
                    history.addAll(restored)
                    messages.removeAllViews()
                    if (restored.isEmpty()) bubble("Empty conversation. Ask NOVA anything.", false)
                    restored.forEach { bubble(it.optString("content"), it.optString("role") == "user") }
                    status.text = "● Ready"
                }
            } catch (_: Exception) {
                runOnUiThread { status.text = "Invalid conversation" }
            }
        }
    }

    private fun pickFile() {
        if (streaming) return
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, false)
        }
        startActivityForResult(intent, filePickerCode)
    }

    @Deprecated("Use Activity Result APIs when the Android client moves to Compose.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == filePickerCode && resultCode == RESULT_OK) {
            data?.data?.let { uploadAttachment(it) }
        }
    }

    private fun loadProject() {
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        thread {
            val result = request("GET", "${base}/api/projects", auth = authHeader())
            if (result.code == 401) {
                expireSession()
                return@thread
            }
            if (result.code !in 200..299) return@thread
            try {
                val projects = JSONArray(result.body)
                if (projects.length() > 0) {
                    projectId = projects.getJSONObject(0).optString("id").ifBlank { null }
                    return@thread
                }
                val id = UUID.randomUUID().toString()
                val created = request(
                    "POST", "${base}/api/projects",
                    JSONObject().put("id", id).put("name", "NOVA Workspace")
                        .put("description", "Default workspace for NOVA conversations and files"),
                    authHeader()
                )
                if (created.code in 200..299) projectId = id
            } catch (_: Exception) {}
        }
    }

    private fun ensureProjectSync(base: String): String {
        projectId?.let { return it }
        val result = request("GET", "$base/api/projects", auth = authHeader())
        if (result.code == 401) throw IllegalStateException("Session expired")
        if (result.code !in 200..299) throw IllegalStateException("Could not load NOVA workspace")
        val projects = JSONArray(result.body)
        if (projects.length() > 0) {
            return projects.getJSONObject(0).optString("id").also { projectId = it }
        }
        val id = UUID.randomUUID().toString()
        val created = request(
            "POST", "$base/api/projects",
            JSONObject().put("id", id).put("name", "NOVA Workspace")
                .put("description", "Default workspace for NOVA conversations and files"),
            authHeader()
        )
        if (created.code !in 200..299) throw IllegalStateException("Could not create NOVA workspace")
        projectId = id
        return id
    }

    private fun uploadAttachment(uri: Uri) {
        if (streaming) return
        status.text = "Uploading file..."
        attachButton.isEnabled = false
        thread {
            try {
                val base = prefs.getString("api", "")?.trimEnd('/') ?: throw IllegalStateException("API URL missing")
                val project = ensureProjectSync(base)
                val resolver = contentResolver
                val name = queryFileName(uri) ?: "upload"
                val mime = resolver.getType(uri) ?: "application/octet-stream"
                val size = queryFileSize(uri)
                if (size > 10L * 1024L * 1024L) throw IllegalArgumentException("File exceeds the 10 MB limit")
                val boundary = "----NOVA-${System.currentTimeMillis()}"
                val connection = (URL("${base}/api/artifacts/upload").openConnection() as HttpURLConnection)
                connection.connectTimeout = 10_000
                connection.readTimeout = 120_000
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Authorization", authHeader())
                connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=${boundary}")
                connection.outputStream.use { out ->
                    fun field(fieldName: String, value: String) {
                        out.write("--${boundary}\r\n".toByteArray())
                        out.write("Content-Disposition: form-data; name=\"${fieldName}\"\r\n\r\n".toByteArray())
                        out.write(value.toByteArray())
                        out.write("\r\n".toByteArray())
                    }
                    field("project_id", project)
                    out.write("--${boundary}\r\n".toByteArray())
                    out.write("Content-Disposition: form-data; name=\"file\"; filename=\"${name.replace("\"", "_")}\"\r\n".toByteArray())
                    out.write("Content-Type: ${mime}\r\n\r\n".toByteArray())
                    resolver.openInputStream(uri)?.use { input ->
                        val buffer = ByteArray(8192)
                        var total = 0L
                        while (true) {
                            val read = input.read(buffer)
                            if (read <= 0) break
                            total += read
                            if (total > 10L * 1024L * 1024L) throw IllegalArgumentException("File exceeds the 10 MB limit")
                            out.write(buffer, 0, read)
                        }
                    } ?: throw IllegalArgumentException("Cannot read selected file")
                    out.write("\r\n--${boundary}--\r\n".toByteArray())
                }
                val code = connection.responseCode
                val body = (if (code >= 400) connection.errorStream else connection.inputStream)?.bufferedReader()?.use { it.readText() } ?: ""
                connection.disconnect()
                if (code !in 200..299) throw IllegalStateException(body.ifBlank { "Upload failed (${code})" })
                val artifact = JSONObject(body)
                val item = JSONObject()
                    .put("artifact_id", artifact.getString("id"))
                    .put("type", if (mime.startsWith("image/")) "image_url" else "file")
                    .put("mime_type", artifact.optString("mime_type", mime))
                    .put("name", artifact.optString("name", name))
                attachments.add(item)
                runOnUiThread {
                    status.text = "Attached: ${item.optString("name")}"
                    progress.visibility = View.VISIBLE
                    progress.text = "Attachments ready: ${attachments.size}"
                    attachButton.isEnabled = true
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = "Upload failed"
                    progress.text = e.message ?: "Could not upload file"
                    attachButton.isEnabled = true
                }
            }
        }
    }

    private fun queryFileName(uri: Uri): String? {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) return cursor.getString(0)
        }
        return uri.lastPathSegment
    }

    private fun queryFileSize(uri: Uri): Long {
        contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) return cursor.getLong(0)
        }
        return -1L
    }

    private fun ensureConversation(userText: String): String? {
        conversationId?.let { return it }
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return null
        val id = UUID.randomUUID().toString()
        val result = request(
            "POST", "$base/api/conversations",
            JSONObject().put("id", id).put("title", userText.take(60).ifBlank { "New chat" }),
            authHeader()
        )
        if (result.code !in 200..299) return null
        conversationId = id
        return id
    }

    private fun saveMessage(conversation: String, role: String, content: String) {
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        request(
            "POST", "$base/api/conversations/$conversation/messages",
            JSONObject().put("id", UUID.randomUUID().toString()).put("role", role).put("content", content),
            authHeader()
        )
    }

    private fun authHeader(): String = "Bearer " + prefs.getString("token", "")

    private fun expireSession() {
        prefs.edit().remove("token").apply()
        runOnUiThread {
            status.text = "Session expired"
            sendButton.isEnabled = false
            newChatButton.isEnabled = false
            authButton.visibility = View.VISIBLE
            authButton.isEnabled = true
        }
    }

    private fun sendMessage() {
        val text = message.text.toString().trim()
        val token = prefs.getString("token", null) ?: return
        if (streaming || text.isBlank()) return
        streaming = true

        val historyArray = JSONArray()
        history.forEach { historyArray.put(it) }

        bubble(text, true)
        message.text.clear()
        sendButton.isEnabled = false
        newChatButton.isEnabled = false
        status.text = "Planning..."
        progress.visibility = View.VISIBLE
        progress.text = "Planning → Tools → Reasoning → Verification"

        val assistant = bubble("NOVA is thinking...", false)
        assistant.setTextColor(Color.LTGRAY)
        val answer = StringBuilder()

        val payload = JSONObject()
            .put("goal", text)
            .put("messages", historyArray)
        projectId?.let { payload.put("project_id", it) }
        val attachmentArray = JSONArray()
        attachments.forEach { attachmentArray.put(JSONObject(it.toString())) }
        payload.put("attachments", attachmentArray)
        val selectedModel = modelSpinner.selectedItem?.toString()?.trim()
        if (!selectedModel.isNullOrBlank() && selectedModel != "Auto") {
            payload.put("model", selectedModel)
        }

        thread {
            val id = ensureConversation(text)
            if (id == null) {
                runOnUiThread {
                    assistant.text = "Could not create conversation."
                    status.text = "Conversation error"
                    streaming = false
                    sendButton.isEnabled = true
                    newChatButton.isEnabled = true
                }
                return@thread
            }
            streamChat(payload, token, assistant, answer, text, id)
        }
    }

    private fun streamChat(
        payload: JSONObject,
        token: String,
        assistant: TextView,
        answer: StringBuilder,
        userText: String,
        conversation: String
    ) {
        var connection: HttpURLConnection? = null
        var finalContent: String? = null
        var failed = false
        try {
            val base = prefs.getString("api", "")!!.trimEnd('/')
            connection = URL("$base/api/stream").openConnection() as HttpURLConnection
            connection.connectTimeout = 10_000
            connection.readTimeout = 120_000
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Accept", "text/event-stream")
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $token")
            connection.outputStream.use {
                it.write(payload.toString().toByteArray(Charsets.UTF_8))
            }

            val code = connection.responseCode
            if (code == 401) {
                failed = true
                prefs.edit().remove("token").apply()
                runOnUiThread {
                    assistant.text = "Session expired. Please sign in again."
                    status.text = "Session expired"
                    sendButton.isEnabled = false
                }
                return
            }
            if (code !in 200..299) {
                failed = true
                val body = connection.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                runOnUiThread {
                    assistant.text = "Stream failed: $body"
                    status.text = "Stream error"
                }
                return
            }

            connection.inputStream.bufferedReader().useLines { lines ->
                lines.forEach { line ->
                    if (!line.startsWith("data:")) return@forEach
                    val raw = line.removePrefix("data:").trim()
                    if (raw.isBlank()) return@forEach
                    try {
                        val event = JSONObject(raw)
                        when (event.optString("type")) {
                            "task.started" -> {
                                runOnUiThread {
                                    progress.visibility = View.VISIBLE
                                    progress.text = "● Task started"
                                    status.text = "Planning..."
                                }
                            }
                            "plan.created" -> {
                                val data = event.optJSONObject("data")
                                val steps = data?.optJSONArray("steps")
                                val count = steps?.length() ?: 0
                                runOnUiThread {
                                    progress.text = "✓ Plan created" + if (count > 0) " • $count steps" else ""
                                    status.text = "Executing plan..."
                                }
                            }
                            "tool.call.delta" -> {
                                val data = event.optJSONObject("data")
                                val name = data?.optString("name").orEmpty()
                                if (name.isNotBlank()) runOnUiThread {
                                    progress.text = "⚙ $name"
                                    status.text = "Using tool..."
                                }
                            }
                            "tool.call.result" -> {
                                val data = event.optJSONObject("data")
                                val name = data?.optString("tool").orEmpty()
                                val success = data?.optBoolean("success", false) ?: false
                                runOnUiThread {
                                    progress.text = (if (success) "✓ " else "✕ ") + name
                                    status.text = if (success) "Tool complete" else "Tool failed"
                                }
                            }
                            "response.delta" -> {
                                val data = event.optJSONObject("data")
                                val delta = data?.optString("delta") ?: event.optString("delta")
                                if (delta.isNotEmpty()) {
                                    answer.append(delta)
                                    val visible = answer.toString()
                                    runOnUiThread {
                                        assistant.setText(visible)
                                        assistant.setTextColor(Color.WHITE)
                                        status.text = "Generating..."
                                    }
                                }
                            }
                            "model.selected" -> {
                                val data = event.optJSONObject("data")
                                val model = data?.optString("model") ?: event.optString("model")
                                if (model.isNotBlank()) runOnUiThread {
                                    status.text = "Using $model"
                                }
                            }
                            "verification" -> {
                                val data = event.optJSONObject("data")
                                val verified = data?.optBoolean("passed", false) ?: event.optBoolean("verified", false)
                                runOnUiThread {
                                    status.text = if (verified) "Verified" else "Verification needs attention"
                                    progress.text = if (verified) "✓ Verification passed" else "⚠ Verification incomplete"
                                }
                            }
                            "response.final" -> {
                                runOnUiThread {
                                    status.text = "Finalizing..."
                                    progress.text = "✓ Response finalized"
                                }
                                val content = event.optString("content")
                                if (content.isNotBlank()) finalContent = content
                            }
                            "task.finished" -> {
                                runOnUiThread {
                                    progress.text = "✓ Task complete"
                                    status.text = "● Ready"
                                }
                            }
                            "provider.failed" -> {
                                val data = event.optJSONObject("data")
                                val model = data?.optString("model").orEmpty()
                                runOnUiThread {
                                    progress.text = "↻ Provider failed" + if (model.isNotBlank()) ": $model" else ""
                                    status.text = "Trying another model..."
                                }
                            }
                            "error" -> {
                                failed = true
                                val error = event.optString("error", "Unknown stream error")
                                runOnUiThread {
                                    assistant.text = error
                                    assistant.setTextColor(Color.rgb(255, 120, 120))
                                    status.text = "Error"
                                }
                            }
                        }
                    } catch (_: Exception) {
                        // Ignore malformed/heartbeat SSE lines.
                    }
                }
            }

            if (finalContent != null && answer.isEmpty()) {
                answer.append(finalContent)
                runOnUiThread { assistant.setText(finalContent) }
            }

            if (!failed) {
                val finalAnswer = answer.toString().ifBlank { finalContent ?: "No response." }
                history.add(JSONObject().put("role", "user").put("content", userText))
                history.add(JSONObject().put("role", "assistant").put("content", finalAnswer))
                thread {
                    saveMessage(conversation, "user", userText)
                    saveMessage(conversation, "assistant", finalAnswer)
                }
                runOnUiThread {
                    assistant.setText(finalAnswer)
                    assistant.setTextColor(Color.WHITE)
                    status.text = "● Ready"
                }
            }
        } catch (e: Exception) {
            failed = true
            runOnUiThread {
                assistant.text = "Connection error: " + (e.message ?: "unknown error")
                assistant.setTextColor(Color.rgb(255, 120, 120))
                status.text = "Offline"
                progress.visibility = View.GONE
            }
        } finally {
            connection?.disconnect()
            runOnUiThread {
                streaming = false
                newChatButton.isEnabled = true
                if (!failed && prefs.getString("token", null) != null) {
                    sendButton.isEnabled = true
                }
            }
        }
    }

    private fun authError(text: String) {
        status.text = text
        authButton.isEnabled = true
    }

    private fun request(
        method: String,
        url: String,
        body: JSONObject? = null,
        auth: String? = null
    ): HttpResult {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 10_000
            c.readTimeout = 60_000
            c.requestMethod = method
            c.setRequestProperty("Accept", "application/json")
            if (auth != null) c.setRequestProperty("Authorization", auth)
            if (body != null) {
                c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = c.responseCode
            val stream = if (code >= 400) c.errorStream else c.inputStream
            val response = stream?.bufferedReader()?.use { it.readText() } ?: ""
            c.disconnect()
            HttpResult(code, response)
        } catch (e: Exception) {
            HttpResult(-1, "ERROR: " + e.message)
        }
    }

    data class HttpResult(val code: Int, val body: String)
}
