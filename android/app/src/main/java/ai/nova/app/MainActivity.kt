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
    private lateinit var loginPanel: LinearLayout
    private lateinit var chatPanel: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (prefs.getString("token", null) != null) showChat()
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    private fun card(color: Int, radius: Int = 18): GradientDrawable =
        GradientDrawable().apply { setColor(color); cornerRadius = dp(radius).toFloat() }

    private fun uiText(value: String, size: Float = 15f): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(Color.WHITE)
    }

    private fun uiInput(hintValue: String, value: String = ""): EditText = EditText(this).apply {
        hint = hintValue
        setText(value)
        textSize = 16f
        setTextColor(Color.WHITE)
        setHintTextColor(Color.rgb(105, 110, 123))
        setPadding(dp(16), 0, dp(16), 0)
        background = card(Color.rgb(28, 30, 38), 14)
        minHeight = dp(54)
        isSingleLine = true
    }

    private fun uiButton(value: String, primary: Boolean = false): TextView = TextView(this).apply {
        text = value
        textSize = 15f
        gravity = Gravity.CENTER
        setTextColor(Color.WHITE)
        background = card(if (primary) Color.rgb(124, 92, 255) else Color.rgb(31, 33, 42), 14)
        minHeight = dp(50)
        setPadding(dp(14), 0, dp(14), 0)
        isClickable = true
    }

    private fun buildUi() {
        val root = FrameLayout(this).apply { setBackgroundColor(Color.rgb(11, 13, 18)) }
        loginPanel = buildLoginPanel()
        chatPanel = buildChatPanel()
        root.addView(loginPanel, FrameLayout.LayoutParams(-1, -1))
        root.addView(chatPanel, FrameLayout.LayoutParams(-1, -1))
        chatPanel.visibility = View.GONE
        setContentView(root)
    }

    private fun buildLoginPanel(): LinearLayout {
        val scroll = ScrollView(this)
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(28), dp(42), dp(28), dp(24))
        }
        scroll.addView(body)

        val logo = ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
        }
        body.addView(logo, LinearLayout.LayoutParams(dp(92), dp(92)).apply {
            gravity = Gravity.CENTER_HORIZONTAL
            bottomMargin = dp(20)
        })

        val title = uiText("Welcome to NOVA", 30f).apply {
            gravity = Gravity.CENTER
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        body.addView(title, LinearLayout.LayoutParams(-1, -2))

        val subtitle = uiText("Think. Create. Research. Build.", 15f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(150, 155, 170))
            setPadding(0, dp(8), 0, dp(30))
        }
        body.addView(subtitle, LinearLayout.LayoutParams(-1, -2))

        email = uiInput("Email", prefs.getString("email", "") ?: "")
        password = uiInput("Password")
        password.inputType = 129
        body.addView(email, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(12) })
        body.addView(password, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(14) })

        authButton = uiButton("Continue", true)
        body.addView(authButton, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(12) })

        val create = uiText("Create a new NOVA account", 14f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(165, 168, 180))
            isClickable = true
        }
        body.addView(create, LinearLayout.LayoutParams(-1, dp(44)))

        val advanced = uiText("Server connection  ›", 13f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(115, 120, 135))
            isClickable = true
            setPadding(0, dp(16), 0, dp(8))
        }
        body.addView(advanced, LinearLayout.LayoutParams(-1, -2))

        serverPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        endpoint = uiInput("Server URL", prefs.getString("api", "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000")
        serverPanel.addView(endpoint, LinearLayout.LayoutParams(-1, dp(54)))
        val hint = uiText("Use your computer's LAN IP on a real phone, or HTTPS in production.", 12f).apply {
            setTextColor(Color.rgb(110, 115, 128))
            setPadding(dp(4), dp(8), dp(4), 0)
        }
        serverPanel.addView(hint)
        body.addView(serverPanel, LinearLayout.LayoutParams(-1, -2))

        status = uiText("", 13f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(245, 115, 115))
            setPadding(0, dp(14), 0, 0)
        }
        body.addView(status, LinearLayout.LayoutParams(-1, -2))

        authButton.setOnClickListener { authenticate() }
        create.setOnClickListener { authenticate() }
        advanced.setOnClickListener {
            serverPanel.visibility = if (serverPanel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }

        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        }
    }

    private fun buildChatPanel(): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(11, 13, 18))
        }

        val top = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(10), dp(8), dp(10), dp(8))
        }
        val menu = uiText("☰", 24f).apply { gravity = Gravity.CENTER; isClickable = true }
        top.addView(menu, LinearLayout.LayoutParams(dp(48), dp(46)))

        val logo = ImageView(this).apply { setImageResource(R.mipmap.ic_launcher); scaleType = ImageView.ScaleType.CENTER_INSIDE }
        top.addView(logo, LinearLayout.LayoutParams(dp(38), dp(38)))

        val nameBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(8), 0, 0, 0) }
        val name = uiText("NOVA", 18f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) }
        status = uiText("Ready", 11f).apply { setTextColor(Color.rgb(145, 150, 165)) }
        nameBox.addView(name)
        nameBox.addView(status)
        top.addView(nameBox, LinearLayout.LayoutParams(0, -2, 1f))

        modelSpinner = Spinner(this)
        top.addView(modelSpinner, LinearLayout.LayoutParams(dp(112), dp(42)))
        root.addView(top)

        val line = View(this).apply { setBackgroundColor(Color.rgb(32, 34, 42)) }
        root.addView(line, LinearLayout.LayoutParams(-1, 1))

        val chatActions = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(7), dp(12), dp(7))
        }
        conversationSpinner = Spinner(this)
        newChatButton = uiButton("+ New chat")
        chatActions.addView(conversationSpinner, LinearLayout.LayoutParams(0, dp(44), 1f))
        chatActions.addView(newChatButton, LinearLayout.LayoutParams(dp(112), dp(44)))
        root.addView(chatActions)

        progress = uiText("", 12f).apply {
            setTextColor(Color.rgb(145, 150, 165))
            setPadding(dp(18), 0, dp(18), dp(6))
            visibility = View.GONE
        }
        root.addView(progress)

        messages = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(8), dp(14), dp(18))
        }
        val scroll = ScrollView(this).apply { addView(messages) }
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))

        val composerOuter = LinearLayout(this).apply { setPadding(dp(10), dp(8), dp(10), dp(12)) }
        val composer = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            background = card(Color.rgb(27, 29, 37), 20)
            setPadding(dp(8), dp(5), dp(6), dp(5))
        }
        message = EditText(this).apply {
            hint = "Message NOVA"
            textSize = 16f
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(100, 105, 118))
            background = null
            minLines = 1
            maxLines = 5
            isEnabled = false
            setPadding(dp(8), dp(4), dp(8), dp(4))
        }
        composer.addView(message, LinearLayout.LayoutParams(0, -2, 1f))
        attachButton = uiText("＋", 24f).apply { gravity = Gravity.CENTER; setTextColor(Color.rgb(160, 164, 175)); isEnabled = false }
        composer.addView(attachButton, LinearLayout.LayoutParams(dp(46), dp(46)))
        sendButton = uiText("↑", 24f).apply {
            gravity = Gravity.CENTER
            background = card(Color.rgb(124, 92, 255), 16)
            isEnabled = false
        }
        composer.addView(sendButton, LinearLayout.LayoutParams(dp(46), dp(46)))
        composerOuter.addView(composer, LinearLayout.LayoutParams(-1, -2))
        root.addView(composerOuter)

        menu.setOnClickListener { showHistoryDrawer() }
        newChatButton.setOnClickListener { newChat() }
        sendButton.setOnClickListener { sendMessage() }
        attachButton.setOnClickListener { pickFile() }

        conversationSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (!loadingConversation && position in conversations.indices) openConversation(conversations[position].optString("id"))
            }
        }
        return root
    }

    private fun field(hintText: String, value: String?): EditText = EditText(this).apply {
        hint = hintText
        setText(value ?: "")
        isSingleLine = true
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
        attachButton.isEnabled = true
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
