package com.wrenchrelay.industrial;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Locale;
import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {
  private static final String HOME = "https://wrenchrelayllc.com/";
  private static final String PRIVACY_URL = "https://wrenchrelayllc.com/privacy-android";
  private static final String DELETE_ACCOUNT_URL = "https://wrenchrelayllc.com/delete-account";
  private static final int REQUEST_SPEECH = 401;
  private static final int REQUEST_FILE_PICKER = 402;
  private WebView web;
  private ProgressBar progress;
  private LinearLayout networkError;
  private ValueCallback<Uri[]> pendingFiles;
  private boolean speechActive;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
    WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView())
        .setAppearanceLightNavigationBars(false);
    LinearLayout screen = new LinearLayout(this);
    screen.setOrientation(LinearLayout.VERTICAL);
    ViewCompat.setOnApplyWindowInsetsListener(screen, (view, insets) -> {
      Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars()
          | WindowInsetsCompat.Type.displayCutout());
      Insets keyboard = insets.getInsets(WindowInsetsCompat.Type.ime());
      view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, keyboard.bottom));
      return WindowInsetsCompat.CONSUMED;
    });
    screen.setBackgroundColor(Color.rgb(7, 17, 31));
    LinearLayout toolbar = new LinearLayout(this);
    toolbar.setPadding(dp(6), dp(4), dp(6), dp(4));
    toolbar.addView(actionButton(R.string.speak_note, v -> startNativeSpeech()),
        new LinearLayout.LayoutParams(0, -2, 1f));
    toolbar.addView(actionButton(R.string.retry, v -> { if (web != null) web.reload(); }),
        new LinearLayout.LayoutParams(0, -2, 1f));
    Button account = actionButton(R.string.account_settings, v -> showPrivacyAndAccountOptions());
    account.setContentDescription(getString(R.string.account_settings_content_description));
    toolbar.addView(account, new LinearLayout.LayoutParams(0, -2, 1.4f));
    screen.addView(toolbar);
    progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
    screen.addView(progress, new LinearLayout.LayoutParams(-1, dp(3)));
    FrameLayout content = new FrameLayout(this);
    web = new WebView(this);
    web.setBackgroundColor(Color.rgb(7, 17, 31));
    content.addView(web, new FrameLayout.LayoutParams(-1, -1));
    networkError = new LinearLayout(this);
    networkError.setOrientation(LinearLayout.VERTICAL);
    networkError.setGravity(Gravity.CENTER);
    networkError.setPadding(dp(28), dp(28), dp(28), dp(28));
    networkError.setBackgroundColor(Color.rgb(7, 17, 31));
    TextView errorText = new TextView(this);
    errorText.setText(R.string.network_error);
    errorText.setTextColor(Color.WHITE);
    errorText.setTextSize(18);
    networkError.addView(errorText);
    networkError.addView(actionButton(R.string.retry, v -> web.reload()));
    networkError.setVisibility(View.GONE);
    content.addView(networkError, new FrameLayout.LayoutParams(-1, -1));
    screen.addView(content, new LinearLayout.LayoutParams(-1, 0, 1f));
    setContentView(screen);
    WebSettings settings = web.getSettings();
    settings.setJavaScriptEnabled(true);
    settings.setDomStorageEnabled(true);
    settings.setAllowFileAccess(false);
    settings.setAllowContentAccess(false);
    settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    settings.setJavaScriptCanOpenWindowsAutomatically(false);
    web.setWebChromeClient(new WebChromeClient() {
      @Override public void onProgressChanged(WebView view, int percent) {
        progress.setProgress(percent);
        progress.setVisibility(percent < 100 ? View.VISIBLE : View.GONE);
      }
      @Override public void onPermissionRequest(PermissionRequest request) {
        // This client uses the device recognition activity, not WebView microphone capture.
        runOnUiThread(() -> {
          request.deny();
          Toast.makeText(MainActivity.this, R.string.microphone_fallback, Toast.LENGTH_SHORT).show();
        });
      }
      @Override public boolean onShowFileChooser(
          WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
        if (!WebHostPolicy.isTrustedHttps(view.getUrl())) {
          callback.onReceiveValue(null);
          return true;
        }
        if (pendingFiles != null) pendingFiles.onReceiveValue(null);
        pendingFiles = callback;
        try {
          startActivityForResult(params.createIntent(), REQUEST_FILE_PICKER);
          return true;
        } catch (ActivityNotFoundException | SecurityException exception) {
          pendingFiles.onReceiveValue(null);
          pendingFiles = null;
          Toast.makeText(MainActivity.this, R.string.file_picker_unavailable, Toast.LENGTH_SHORT).show();
          return true; // The callback was already completed.
        }
      }
    });
    web.setWebViewClient(new WebViewClient() {
      @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
        networkError.setVisibility(View.GONE);
        progress.setVisibility(View.VISIBLE);
      }
      @Override public void onPageFinished(WebView view, String url) {
        progress.setVisibility(View.GONE);
      }
      @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
        if (request.isForMainFrame()) showNetworkError();
      }
      @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse response) {
        if (request.isForMainFrame() && response.getStatusCode() >= 400) showNetworkError();
      }
      @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        if (!request.isForMainFrame()) return false;
        String url = request.getUrl().toString();
        if (WebHostPolicy.isTrustedHttps(url)) return false;
        if (WebHostPolicy.canOpenExternally(url)) openExternal(url);
        return true;
      }
    });
    if (state == null || web.restoreState(state) == null) web.loadUrl(HOME);
  }

  private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

  private Button actionButton(int label, View.OnClickListener listener) {
    Button button = new Button(this);
    button.setText(label);
    button.setAllCaps(false);
    button.setTextSize(13);
    button.setMinWidth(0);
    button.setOnClickListener(listener);
    return button;
  }

  private void showNetworkError() {
    progress.setVisibility(View.GONE);
    networkError.setVisibility(View.VISIBLE);
  }

  private void startNativeSpeech() {
    if (speechActive || web == null || !WebHostPolicy.isTrustedHttps(web.getUrl())) return;
    speechActive = true;
    final String script;
    try {
      try (java.io.InputStream input = getAssets().open("native-voice.js")) {
        java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int count;
        while ((count = input.read(buffer)) != -1) bytes.write(buffer, 0, count);
        script = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
      }
    } catch (IOException error) {
      speechActive = false;
      Toast.makeText(this, R.string.microphone_fallback, Toast.LENGTH_LONG).show();
      return;
    }
    web.evaluateJavascript(script + "\nwindow.__wrNativeVoice.capture();", captured -> {
      if (isFinishing() || isDestroyed() || web == null) return;
      if (!"true".equals(captured)) {
        speechActive = false;
        new AlertDialog.Builder(this).setTitle(R.string.speak_note)
            .setMessage(R.string.select_notes_first).setPositiveButton(android.R.string.ok, null).show();
        return;
      }
      Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
      intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
      intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag());
      intent.putExtra(RecognizerIntent.EXTRA_PROMPT, getString(R.string.speech_prompt));
      try {
        startActivityForResult(intent, REQUEST_SPEECH);
      } catch (ActivityNotFoundException | SecurityException error) {
        speechActive = false;
        Toast.makeText(this, R.string.recognizer_unavailable, Toast.LENGTH_LONG).show();
      }
    });
  }

  private void reviewSpeech(String transcript) {
    EditText editor = new EditText(this);
    editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
    editor.setMinLines(3);
    editor.setText(transcript);
    new AlertDialog.Builder(this).setTitle(R.string.review_speech).setView(editor)
        .setPositiveButton(R.string.use_note, (dialog, which) -> {
          String text = editor.getText().toString().trim();
          if (text.isEmpty() || web == null || !WebHostPolicy.isTrustedHttps(web.getUrl())) return;
          String js = "Boolean(window.__wrNativeVoice && window.__wrNativeVoice.apply("
              + JSONObject.quote(text) + "));";
          web.evaluateJavascript(js, applied -> {
            if (isFinishing() || isDestroyed() || web == null) return;
            if ("true".equals(applied)) {
              Toast.makeText(this, R.string.note_added, Toast.LENGTH_SHORT).show();
            } else {
              new AlertDialog.Builder(this).setMessage(R.string.notes_changed)
                  .setPositiveButton(R.string.copy_note, (d, w) -> copyNote(text))
                  .setNegativeButton(R.string.cancel, null).show();
            }
          });
        })
        .setNeutralButton(R.string.copy_note, (dialog, which) -> copyNote(editor.getText().toString()))
        .setNegativeButton(R.string.cancel, null).show();
  }

  private void copyNote(String text) {
    ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
    if (clipboard != null) {
      ClipData clip = ClipData.newPlainText(getString(R.string.app_name), text);
      if (android.os.Build.VERSION.SDK_INT >= 33) {
        android.os.PersistableBundle extras = new android.os.PersistableBundle();
        extras.putBoolean("android.content.extra.IS_SENSITIVE", true);
        clip.getDescription().setExtras(extras);
      }
      clipboard.setPrimaryClip(clip);
      Toast.makeText(this, R.string.note_copied, Toast.LENGTH_SHORT).show();
    }
  }

  private void showPrivacyAndAccountOptions() {
    new AlertDialog.Builder(this).setTitle(R.string.account_dialog_title)
        .setItems(new String[]{getString(R.string.privacy_action), getString(R.string.deletion_action),
            getString(R.string.about_app)}, (dialog, which) -> {
          if (which == 0) showClientPrivacy();
          else if (which == 1) openAccountPage(DELETE_ACCOUNT_URL);
          else showAbout();
        }).setNegativeButton(R.string.cancel, null).show();
  }

  private void showClientPrivacy() {
    TextView notice = new TextView(this);
    notice.setText(R.string.client_privacy_notice);
    notice.setTextSize(16);
    notice.setPadding(dp(22), dp(16), dp(22), dp(16));
    ScrollView scroll = new ScrollView(this);
    scroll.addView(notice);
    new AlertDialog.Builder(this).setTitle(R.string.privacy_action).setView(scroll)
        .setPositiveButton(android.R.string.ok, null)
        .setNeutralButton(R.string.full_privacy, (dialog, which) -> openAccountPage(PRIVACY_URL)).show();
  }

  private void showAbout() {
    String version = "";
    try { version = getPackageManager().getPackageInfo(getPackageName(), 0).versionName; }
    catch (android.content.pm.PackageManager.NameNotFoundException ignored) {}
    boolean debug = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
    String text = getString(R.string.app_name) + "\n" + getPackageName() + "\n"
        + getString(R.string.app_version, version) + "\n"
        + (debug ? getString(R.string.qa_build) : getString(R.string.app_operator));
    new AlertDialog.Builder(this).setTitle(R.string.about_app).setMessage(text)
        .setPositiveButton(android.R.string.ok, null).show();
  }

  private void openAccountPage(String url) {
    if (!WebHostPolicy.isTrustedHttps(url)) return;
    openExternal(url);
  }

  private void openExternal(String url) {
    try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)).addCategory(Intent.CATEGORY_BROWSABLE)); }
    catch (ActivityNotFoundException | SecurityException error) {
      Toast.makeText(this, R.string.open_failed, Toast.LENGTH_LONG).show();
    }
  }

  @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    super.onActivityResult(requestCode, resultCode, data);
    if (requestCode == REQUEST_SPEECH) speechActive = false;
    if (requestCode == REQUEST_SPEECH && resultCode == Activity.RESULT_OK && data != null) {
      ArrayList<String> results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
      if (results != null && !results.isEmpty()) reviewSpeech(results.get(0));
    }
    if (requestCode == REQUEST_FILE_PICKER && pendingFiles != null) {
      pendingFiles.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
      pendingFiles = null;
    }
  }

  @Override protected void onSaveInstanceState(Bundle state) {
    if (web != null) web.saveState(state);
    super.onSaveInstanceState(state);
  }

  @Override public void onBackPressed() {
    if (web != null && web.canGoBack()) web.goBack();
    else super.onBackPressed();
  }

  @Override protected void onDestroy() {
    if (pendingFiles != null) { pendingFiles.onReceiveValue(null); pendingFiles = null; }
    if (web != null) { web.destroy(); web = null; }
    super.onDestroy();
  }
}
