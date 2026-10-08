package ai.nova.app

import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.content.Intent
import android.content.MutableContextWrapper
import android.net.Uri
import android.provider.OpenableColumns
import android.view.View
import android.view.Gravity
import android.widget.*
import android.app.Dialog
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.security.SecureRandom
import android.util.Base64
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private val prefs by lazy { getSharedPreferences("nova", MODE_PRIVATE) }
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var message: EditText
    private lateinit var status: TextView
    private lateinit var progress: TextView
    private lateinit var messages: LinearLayout
    private lateinit var sendButton: TextView
    private lateinit var attachButton: TextView
    private val attachments = mutableListOf<JSONObject>()
    private var projectId: String? = null
    private val filePickerCode = 7001
    private lateinit var authButton: TextView
    private lateinit var modelSpinner: Spinner
    private lateinit var conversationSpinner: Spinner
    private lateinit var newChatButton: TextView
    private val conversations = mutableListOf<JSONObject>()
    private var conversationId: String? = null
    private var loadingConversation = false
    private val history = mutableListOf<JSONObject>()
    private var streaming = false
    private lateinit var loginPanel: LinearLayout
    private lateinit var chatPanel: LinearLayout
    private lateinit var authStatus: TextView
    private lateinit var emptyState: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (prefs.getString("token", null) != null) showChat()
        handleOAuthIntent(intent)
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
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(9, 10, 14))
        }
        val scroll = ScrollView(this).apply { isFillViewport = true; overScrollMode = View.OVER_SCROLL_NEVER }
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(28), dp(34), dp(28), dp(24))
        }
        scroll.addView(body)

        val logo = ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
        }
        body.addView(logo, LinearLayout.LayoutParams(dp(96), dp(96)).apply { bottomMargin = dp(12) })
        body.addView(uiText("NOVA", 36f).apply {
            gravity = Gravity.CENTER
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            letterSpacing = 0.04f
        }, LinearLayout.LayoutParams(-1, -2))
        body.addView(uiText("Your intelligent workspace", 15f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(148, 151, 162))
            setPadding(0, dp(4), 0, dp(28))
        }, LinearLayout.LayoutParams(-1, -2))

        val welcomeBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = card(Color.rgb(18, 20, 27), 22)
            setPadding(dp(20), dp(18), dp(20), dp(18))
        }
        welcomeBox.addView(uiText("Think. Create. Research. Build.", 19f).apply {
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        })
        welcomeBox.addView(uiText("One premium interface for reasoning, coding, research, files, memory and agent tasks.", 13f).apply {
            setTextColor(Color.rgb(154, 158, 171))
            setPadding(0, dp(7), 0, 0)
        })
        body.addView(welcomeBox, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(18) })

        // Consumer sign-in choices
        val googleLogin = uiButton("G   Continue with Google", true).apply { background = card(Color.rgb(29,31,38), 18); setTextColor(Color.WHITE) }
        val emailLogin = uiButton("@   Continue with Email", true).apply { background = card(Color.rgb(29,31,38), 18); setTextColor(Color.WHITE) }
        val xLogin = uiButton("X   Continue with X", true).apply { background = card(Color.rgb(29,31,38), 18); setTextColor(Color.WHITE) }
        body.addView(googleLogin, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(10) })
        body.addView(emailLogin, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(10) })
        body.addView(xLogin, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(18) })

        email = uiInput("Email", prefs.getString("email", "") ?: "")
        password = uiInput("Password")
        password.inputType = 129
        body.addView(email, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(10) })
        body.addView(password, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(12) })

        authButton = uiButton("Sign in with Email", true).apply {
            textSize = 16f
            background = card(Color.rgb(245, 246, 248), 16)
            setTextColor(Color.rgb(15, 16, 20))
        }
        body.addView(authButton, LinearLayout.LayoutParams(-1, dp(56)).apply { bottomMargin = dp(10) })

        val create = uiText("Create a new NOVA account", 14f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(184, 187, 198))
            isClickable = true
        }
        body.addView(create, LinearLayout.LayoutParams(-1, dp(44)))

        // Server configuration is intentionally hidden from the consumer login UI.
        // NOVA manages its API endpoint internally.

        authStatus = uiText("", 13f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(245, 120, 120))
            setPadding(0, dp(4), 0, 0)
        }
        body.addView(authStatus, LinearLayout.LayoutParams(-1, -2))
        body.addView(uiText("By continuing, you agree to the NOVA terms and privacy policy.", 11f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(84, 88, 100))
            setPadding(dp(12), dp(18), dp(12), 0)
        }, LinearLayout.LayoutParams(-1, -2))

        authButton.setOnClickListener { authenticate() }
        emailLogin.setOnClickListener { email.requestFocus() }
        googleLogin.setOnClickListener { signInWithGoogle() }
        xLogin.setOnClickListener { startOAuth("x") }
        create.setOnClickListener { authenticate() }

        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        return root
    }


    private fun signInWithGoogle() {
        val clientId = BuildConfig.GOOGLE_WEB_CLIENT_ID.trim()
        if (clientId.isBlank()) {
            authStatus.text = "Google sign-in is not configured yet."
            return
        }
        // Launch Android native Google account selection directly.
        // No NOVA server URL or browser redirect is used here.
        authStatus.text = "Opening Google sign-in…"
        launchGoogleCredentialFlow(clientId)
    }

    private fun launchGoogleCredentialFlow(serverClientId: String) {
        lifecycleScope.launch {
            try {
                val nonceBytes = ByteArray(32)
                SecureRandom().nextBytes(nonceBytes)
                val nonce = Base64.encodeToString(
                    nonceBytes,
                    Base64.NO_WRAP or Base64.URL_SAFE or Base64.NO_PADDING
                )
                val option = GetSignInWithGoogleOption.Builder(serverClientId)
                    .setNonce(nonce)
                    .build()
                val credentialRequest = GetCredentialRequest.Builder()
                    .addCredentialOption(option)
                    .build()
                val manager = CredentialManager.create(this@MainActivity)
                val mutableContext = MutableContextWrapper(this@MainActivity)
                val result = manager.getCredential(
                    context = mutableContext,
                    request = credentialRequest
                )
                val credential = result.credential
                if (credential !is CustomCredential ||
                    credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
                ) {
                    throw IllegalStateException("Unexpected Google credential")
                }
                val googleCredential = try {
                    GoogleIdTokenCredential.createFrom(credential.data)
                } catch (e: GoogleIdTokenParsingException) {
                    throw IllegalStateException("Invalid Google credential", e)
                }
                exchangeGoogleIdToken(googleCredential.idToken)
            } catch (_: Exception) {
                authStatus.text = "Google sign-in was cancelled or could not be completed."
            }
        }
    }

    private fun exchangeGoogleIdToken(idToken: String) {
        authStatus.text = "Completing secure sign-in…"
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val base = prefs.getString("api", "http://10.0.2.2:8000")?.trim()?.trimEnd('/')
                    ?: "http://10.0.2.2:8000"
                val result = request(
                    "POST",
                    "$base/api/auth/google/mobile",
                    JSONObject().put("id_token", idToken)
                )
                if (result.code !in 200..299) throw IllegalStateException("Google authentication failed")
                val token = JSONObject(result.body).optString("access_token")
                if (token.isBlank()) throw IllegalStateException("NOVA token missing")
                prefs.edit().putString("token", token).apply()
                withContext(Dispatchers.Main) { showChat() }
            } catch (_: Exception) {
                withContext(Dispatchers.Main) {
                    authStatus.text = "Google sign-in could not be completed. Please try again."
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        handleOAuthIntent(intent)
    }

    private fun handleOAuthIntent(intent: Intent?) {
        val data = intent?.data ?: return
        if (data.scheme == "nova" && data.host == "auth") {
            val code = data.getQueryParameter("code")
            if (!code.isNullOrBlank()) exchangeOAuthCode(code)
        }
    }

    private fun exchangeOAuthCode(code: String) {
        authStatus.text = "Completing secure sign-in…"
        thread {
            try {
                val base = prefs.getString("api", "http://10.0.2.2:8000")?.trim()?.trimEnd('/')
                    ?: "http://10.0.2.2:8000"
                val conn = (URL("$base/api/auth/oauth/exchange").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10000
                    readTimeout = 15000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
                conn.outputStream.use { it.write(JSONObject().put("code", code).toString().toByteArray()) }
                val responseBody = if (conn.responseCode in 200..299) {
                    conn.inputStream.bufferedReader().use { it.readText() }
                } else {
                    conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                }
                val token = JSONObject(responseBody).optString("access_token")
                if (conn.responseCode !in 200..299 || token.isBlank()) {
                    throw IllegalStateException("OAuth exchange failed")
                }
                prefs.edit().putString("token", token).apply()
                runOnUiThread { showChat() }
            } catch (_: Exception) {
                runOnUiThread { authStatus.text = "Sign-in could not be completed. Please try again." }
            }
        }
    }

    private fun startOAuth(provider: String) {
        val base = prefs.getString("api", "http://10.0.2.2:8000")?.trim()?.trimEnd('/')
            ?: "http://10.0.2.2:8000"
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("$base/api/auth/$provider/start")))
        } catch (_: Exception) {
            authStatus.text = "Could not open sign-in."
        }
    }

    private fun buildChatPanel(): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(9, 10, 14))
        }
        val top = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(10), dp(8), dp(10), dp(7))
        }
        val menu = uiText("☰", 23f).apply { gravity = Gravity.CENTER; setTextColor(Color.rgb(225, 227, 232)); isClickable = true }
        top.addView(menu, LinearLayout.LayoutParams(dp(46), dp(44)))
        val logo = ImageView(this).apply { setImageResource(R.mipmap.ic_launcher); scaleType = ImageView.ScaleType.CENTER_INSIDE }
        top.addView(logo, LinearLayout.LayoutParams(dp(36), dp(36)))
        val nameBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(8), 0, 0, 0) }
        nameBox.addView(uiText("NOVA", 17f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) })
        status = uiText("Ready", 10.5f).apply { setTextColor(Color.rgb(122, 126, 139)) }
        nameBox.addView(status)
        top.addView(nameBox, LinearLayout.LayoutParams(0, -2, 1f))
        modelSpinner = Spinner(this).apply { background = card(Color.rgb(22, 24, 31), 13); setPadding(dp(6), 0, dp(5), 0) }
        top.addView(modelSpinner, LinearLayout.LayoutParams(dp(118), dp(40)))
        val more = uiText("⋯", 24f).apply { gravity = Gravity.CENTER; setTextColor(Color.rgb(190, 193, 202)); isClickable = true }
        top.addView(more, LinearLayout.LayoutParams(dp(40), dp(44)))
        root.addView(top)
        root.addView(View(this).apply { setBackgroundColor(Color.rgb(27, 29, 36)) }, LinearLayout.LayoutParams(-1, 1))

        val chatActions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(5)) }
        conversationSpinner = Spinner(this).apply { background = card(Color.rgb(17, 19, 25), 13); setPadding(dp(8), 0, dp(5), 0) }
        newChatButton = uiButton("+ New chat").apply { textSize = 13f; background = card(Color.rgb(22, 24, 31), 13) }
        chatActions.addView(conversationSpinner, LinearLayout.LayoutParams(0, dp(42), 1f).apply { rightMargin = dp(8) })
        chatActions.addView(newChatButton, LinearLayout.LayoutParams(dp(104), dp(42)))
        root.addView(chatActions)

        progress = uiText("", 11.5f).apply {
            setTextColor(Color.rgb(154, 158, 170))
            gravity = Gravity.CENTER_VERTICAL
            background = card(Color.rgb(15, 17, 23), 12)
            setPadding(dp(12), 0, dp(12), 0)
            visibility = View.GONE
        }
        root.addView(progress, LinearLayout.LayoutParams(-1, dp(34)).apply {
            leftMargin = dp(12); rightMargin = dp(12); topMargin = dp(2); bottomMargin = dp(3)
        })

        val contentScroll = ScrollView(this).apply { overScrollMode = View.OVER_SCROLL_NEVER }
        val content = FrameLayout(this)
        messages = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(8), dp(14), dp(24))
        }
        content.addView(messages, FrameLayout.LayoutParams(-1, -1))

        val empty = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(32), dp(30), dp(32), dp(20))
        }
        val emptyLogo = ImageView(this).apply { setImageResource(R.mipmap.ic_launcher); scaleType = ImageView.ScaleType.CENTER_INSIDE }
        empty.addView(emptyLogo, LinearLayout.LayoutParams(dp(72), dp(72)).apply { bottomMargin = dp(10) })
        empty.addView(uiText("How can NOVA help?", 26f).apply {
            gravity = Gravity.CENTER
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }, LinearLayout.LayoutParams(-1, -2))
        empty.addView(uiText("Reason deeply, research the web, write code, analyze files, and build with you.", 13f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(128, 132, 145))
            setPadding(0, dp(8), 0, dp(18))
        }, LinearLayout.LayoutParams(-1, -2))
        val chips = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER }
        fun chip(label: String, prompt: String) {
            val c = uiText(label, 13f).apply {
                gravity = Gravity.CENTER
                setTextColor(Color.rgb(200, 203, 211))
                background = card(Color.rgb(20, 22, 29), 16)
                setPadding(dp(16), 0, dp(16), 0)
                isClickable = true
                setOnClickListener { message.setText(prompt); message.setSelection(message.text.length); message.requestFocus() }
            }
            chips.addView(c, LinearLayout.LayoutParams(-1, dp(42)).apply { bottomMargin = dp(8) })
        }
        chip("Research a topic", "Research this topic and give me a verified summary.")
        chip("Write something", "Help me write this clearly and professionally.")
        chip("Build with code", "Help me design and implement this feature.")
        empty.addView(chips, LinearLayout.LayoutParams(-1, -2))
        content.addView(empty, FrameLayout.LayoutParams(-1, -1))
        emptyState = empty
        contentScroll.addView(content)
        root.addView(contentScroll, LinearLayout.LayoutParams(-1, 0, 1f))

        val composerOuter = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(10), dp(7), dp(10), dp(12)) }
        val attachmentStrip = uiText("", 11f).apply { setTextColor(Color.rgb(160, 164, 176)); visibility = View.GONE }
        composerOuter.addView(attachmentStrip, LinearLayout.LayoutParams(-1, dp(28)))
        val composer = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            background = card(Color.rgb(23, 25, 32), 22)
            setPadding(dp(7), dp(5), dp(6), dp(5))
        }
        message = EditText(this).apply {
            hint = "Message NOVA"
            textSize = 16f
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(91, 95, 108))
            background = null
            minLines = 1
            maxLines = 5
            isEnabled = false
            setPadding(dp(9), dp(4), dp(7), dp(4))
            imeOptions = android.view.inputmethod.EditorInfo.IME_ACTION_SEND
        }
        composer.addView(message, LinearLayout.LayoutParams(0, -2, 1f))
        attachButton = uiText("＋", 24f).apply { gravity = Gravity.CENTER; setTextColor(Color.rgb(172, 175, 186)); isEnabled = false; isClickable = true }
        composer.addView(attachButton, LinearLayout.LayoutParams(dp(44), dp(44)))
        sendButton = uiText("↑", 23f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(10, 11, 14))
            background = card(Color.rgb(245, 246, 248), 16)
            isEnabled = false
        }
        composer.addView(sendButton, LinearLayout.LayoutParams(dp(44), dp(44)))
        composerOuter.addView(composer, LinearLayout.LayoutParams(-1, -2))
        root.addView(composerOuter)

        menu.setOnClickListener { showHistoryDrawer() }
        more.setOnClickListener { showSettingsDialog() }
        newChatButton.setOnClickListener { newChat() }
        sendButton.setOnClickListener { sendMessage() }
        attachButton.setOnClickListener { pickFile() }
        message.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == android.view.inputmethod.EditorInfo.IME_ACTION_SEND) { sendMessage(); true } else false
        }
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

    private fun bubble(value: String, user: Boolean): TextView {
        if (::emptyState.isInitialized) emptyState.visibility = View.GONE
        val view = TextView(this).apply {
            text = value
            textSize = 16f
            setTextColor(Color.WHITE)
            setPadding(dp(16), dp(13), dp(16), dp(13))
            background = if (user) card(Color.rgb(42, 45, 55), 18) else ColorDrawable(Color.TRANSPARENT)
        }
        val row = LinearLayout(this).apply {
            gravity = if (user) Gravity.END else Gravity.START
            setPadding(dp(4), dp(4), dp(4), dp(4))
            addView(view, LinearLayout.LayoutParams(if (user) dp(315) else -1, -2))
        }
        messages.addView(row, LinearLayout.LayoutParams(-1, -2))
        return view
    }


    private fun showHistoryDrawer() {
        val dialog = Dialog(this)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(16))
            setBackgroundColor(Color.rgb(13, 15, 20))
        }
        val head = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        head.addView(uiText("Chats", 24f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) }, LinearLayout.LayoutParams(0, -2, 1f))
        head.addView(uiText("×", 26f).apply {
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(150, 154, 166))
            isClickable = true
            setOnClickListener { dialog.dismiss() }
        }, LinearLayout.LayoutParams(dp(42), dp(42)))
        panel.addView(head, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })

        val newChat = uiButton("+ New chat", true).apply {
            textSize = 14f
            background = card(Color.rgb(245, 246, 248), 14)
            setTextColor(Color.rgb(13, 14, 18))
        }
        panel.addView(newChat, LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(10) })
        val search = uiInput("Search chats")
        panel.addView(search, LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(12) })

        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        panel.addView(ScrollView(this).apply { addView(list) }, LinearLayout.LayoutParams(-1, 0, 1f))
        fun render(filter: String = "") {
            list.removeAllViews()
            conversations.filter { it.optString("title", "Chat").contains(filter, ignoreCase = true) }.forEach { item ->
                val row = uiText(item.optString("title", "Chat"), 14f).apply {
                    setTextColor(Color.rgb(211, 214, 222))
                    setPadding(dp(14), 0, dp(14), 0)
                    gravity = Gravity.CENTER_VERTICAL
                    background = card(Color.rgb(20, 22, 29), 12)
                    isClickable = true
                    setOnClickListener { dialog.dismiss(); openConversation(item.optString("id")) }
                }
                list.addView(row, LinearLayout.LayoutParams(-1, dp(50)).apply { bottomMargin = dp(7) })
            }
            if (list.childCount == 0) list.addView(uiText("No chats found.", 13f).apply {
                setTextColor(Color.rgb(105, 109, 122)); setPadding(dp(8), dp(16), dp(8), dp(16))
            })
        }
        render()
        search.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { render(s?.toString().orEmpty()) }
            override fun afterTextChanged(s: android.text.Editable?) = Unit
        })

        val settings = uiText("⚙  Settings", 14f).apply {
            setTextColor(Color.rgb(172, 176, 187))
            setPadding(dp(14), 0, dp(14), 0)
            gravity = Gravity.CENTER_VERTICAL
            background = card(Color.rgb(18, 20, 26), 12)
            isClickable = true
            setOnClickListener { dialog.dismiss(); showSettingsDialog() }
        }
        panel.addView(settings, LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(10) })
        newChat.setOnClickListener { dialog.dismiss(); newChat() }

        dialog.setContentView(panel)
        dialog.window?.setBackgroundDrawable(card(Color.rgb(13, 15, 20), 22))
        dialog.show()
        dialog.window?.setLayout(dp(340), -1)
        dialog.window?.setGravity(Gravity.START or Gravity.CENTER_VERTICAL)
    }

    private fun showSettingsDialog() {
        val dialog = Dialog(this)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(22), dp(20), dp(18))
            setBackgroundColor(Color.rgb(14, 16, 22))
        }
        panel.addView(uiText("NOVA Settings", 22f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(16) })
        val logout = uiText("Sign out", 14f).apply {
            setTextColor(Color.rgb(245, 120, 120)); setPadding(dp(14), 0, dp(14), 0); gravity = Gravity.CENTER_VERTICAL
            background = card(Color.rgb(25, 18, 21), 13); isClickable = true
            setOnClickListener {
                dialog.dismiss()
                prefs.edit().remove("token").apply()
                conversationId = null; history.clear(); conversations.clear(); messages.removeAllViews()
                clearGoogleCredentialState()
                showLogin()
            }
        }
        panel.addView(logout, LinearLayout.LayoutParams(-1, dp(48)))
        dialog.setContentView(panel)
        dialog.window?.setBackgroundDrawable(card(Color.rgb(14, 16, 22), 20))
        dialog.show()
        dialog.window?.setLayout(dp(330), -2)
        dialog.window?.setGravity(Gravity.CENTER)
    }

    private fun showConnectionDialog() {
        val dialog = Dialog(this)
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(22), dp(20), dp(18))
            setBackgroundColor(Color.rgb(14, 16, 22))
        }
        panel.addView(uiText("Server connection", 21f).apply { setTypeface(typeface, android.graphics.Typeface.BOLD) }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })
        val input = uiInput("Server URL", prefs.getString("api", "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000")
        panel.addView(input, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(10) })
        panel.addView(uiText("Use HTTPS in production. HTTP development traffic is permitted by NOVA so Android does not block a local server.", 11f).apply {
            setTextColor(Color.rgb(106, 110, 123))
        }, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(14) })
        val save = uiButton("Save & test", true).apply {
            background = card(Color.rgb(245, 246, 248), 14); setTextColor(Color.rgb(13, 14, 18))
        }
        panel.addView(save, LinearLayout.LayoutParams(-1, dp(50)))
        save.setOnClickListener {
            val value = input.text.toString().trim().trimEnd('/')
            if (value.isBlank()) return@setOnClickListener
            prefs.edit().putString("api", value).apply()
            dialog.dismiss(); testConnection()
        }
        dialog.setContentView(panel)
        dialog.window?.setBackgroundDrawable(card(Color.rgb(14, 16, 22), 20))
        dialog.show()
        dialog.window?.setLayout(dp(340), -2)
        dialog.window?.setGravity(Gravity.CENTER)
    }

    private fun testConnection() {
        val base = prefs.getString("api", "http://10.0.2.2:8000")?.trim()?.trimEnd('/') ?: "http://10.0.2.2:8000"
        authStatus.text = "Checking NOVA server..."
        thread {
            val result = request("GET", "$base/api/health")
            runOnUiThread {
                if (result.code in 200..299) {
                    authStatus.setTextColor(Color.rgb(100, 220, 150))
                    authStatus.text = "● NOVA server is reachable"
                } else {
                    authStatus.setTextColor(Color.rgb(245, 120, 120))
                    authStatus.text = "Could not reach NOVA (\${result.code}). Check the server address."
                }
            }
        }
    }

    private fun clearGoogleCredentialState() {
        lifecycleScope.launch {
            try {
                CredentialManager.create(this@MainActivity).clearCredentialState(
                    androidx.credentials.ClearCredentialStateRequest()
                )
            } catch (_: Exception) {
                // Credential state cleanup is best-effort during sign-out.
            }
        }
    }

    private fun authenticate() {
        val base = prefs.getString("api", "http://10.0.2.2:8000")?.trim()?.trimEnd('/') ?: "http://10.0.2.2:8000"
        val userEmail = email.text.toString().trim()
        val userPassword = password.text.toString()
        if (base.isBlank() || userEmail.isBlank() || userPassword.length < 8) {
            authStatus.text = "Enter your email and an 8+ character password."
            return
        }
        prefs.edit().putString("api", base).putString("email", userEmail).apply()
        authButton.isEnabled = false
        authStatus.text = "Signing in..."
        thread {
            val login = request("POST", "$base/api/auth/login",
                JSONObject().put("email", userEmail).put("password", userPassword))
            if (login.code == 401 || login.code == 404) {
                val register = request("POST", "$base/api/auth/register",
                    JSONObject().put("email", userEmail).put("password", userPassword))
                if (register.code in 200..299) {
                    finishLogin(request("POST", "$base/api/auth/login",
                        JSONObject().put("email", userEmail).put("password", userPassword)))
                } else runOnUiThread { authError("Could not create the account. Check the server and try again.") }
            } else finishLogin(login)
        }
    }

    private fun finishLogin(result: HttpResult) {
        if (result.code !in 200..299) {
            runOnUiThread { authError("Could not sign in. Check your connection and credentials.") }
            return
        }
        try {
            val token = JSONObject(result.body).getString("access_token")
            prefs.edit().putString("token", token).apply()
            runOnUiThread { showChat() }
        } catch (_: Exception) {
            runOnUiThread { authError("Invalid server response.") }
        }
    }

    private fun showLogin() {
        loginPanel.visibility = View.VISIBLE
        chatPanel.visibility = View.GONE
        authButton.isEnabled = true
    }

    private fun showChat() {
        loginPanel.visibility = View.GONE
        chatPanel.visibility = View.VISIBLE
        message.isEnabled = true
        sendButton.isEnabled = true
        newChatButton.isEnabled = true
        status.text = "● Ready"
        modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, arrayOf("Auto"))
        loadModels()
        loadProject()
        loadConversations()
        if (messages.childCount == 0 && ::emptyState.isInitialized) emptyState.visibility = View.VISIBLE
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
        if (::emptyState.isInitialized) emptyState.visibility = View.VISIBLE
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
                    if (restored.isEmpty()) {
                        if (::emptyState.isInitialized) emptyState.visibility = View.VISIBLE
                    } else {
                        restored.forEach { bubble(it.optString("content"), it.optString("role") == "user") }
                    }
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
            authStatus.text = "Session expired. Please sign in again."
            sendButton.isEnabled = false
            newChatButton.isEnabled = false
            showLogin()
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
                    showLogin()
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
        authStatus.text = text
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