package com.wrenchrelay.industrial;

import android.Manifest;
import androidx.appcompat.app.AlertDialog;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import android.widget.Button;
import android.widget.LinearLayout;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
  private static final String HOME = "https://wrenchrelayllc.com/";
  private static final String PRIVACY_URL = "https://wrenchrelayllc.com/privacy";
  private static final String DELETE_ACCOUNT_URL = "https://wrenchrelayllc.com/delete-account";
  private static final int REQUEST_MICROPHONE = 401;
  private static final int REQUEST_FILE_PICKER = 402;
  private WebView web;
  private PermissionRequest pendingAudioPermission;
  private ValueCallback<Uri[]> pendingFiles;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    LinearLayout screen = new LinearLayout(this);
    screen.setOrientation(LinearLayout.VERTICAL);
    Button accountSettings = new Button(this);
    accountSettings.setText(R.string.account_settings);
    accountSettings.setContentDescription(getString(R.string.account_settings_content_description));
    accountSettings.setOnClickListener(view -> showPrivacyAndAccountOptions());
    screen.addView(accountSettings, new LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
    web = new WebView(this);
    screen.addView(web, new LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
    setContentView(screen);
    WebSettings settings = web.getSettings();
    settings.setJavaScriptEnabled(true);
    settings.setDomStorageEnabled(true);
    settings.setAllowFileAccess(false);
    settings.setAllowContentAccess(false);
    settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
    settings.setJavaScriptCanOpenWindowsAutomatically(false);

    web.setWebChromeClient(new WebChromeClient() {
      @Override public void onPermissionRequest(PermissionRequest request) {
        runOnUiThread(() -> handleWebPermission(request));
      }

      @Override public void onPermissionRequestCanceled(PermissionRequest request) {
        if (pendingAudioPermission == request) pendingAudioPermission = null;
      }

      @Override public boolean onShowFileChooser(
          WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
        if (pendingFiles != null) pendingFiles.onReceiveValue(null);
        pendingFiles = callback;
        try {
          startActivityForResult(params.createIntent(), REQUEST_FILE_PICKER);
          return true;
        } catch (ActivityNotFoundException | SecurityException exception) {
          pendingFiles.onReceiveValue(null);
          pendingFiles = null;
          Toast.makeText(MainActivity.this, getString(R.string.file_picker_unavailable), Toast.LENGTH_SHORT).show();
          return false;
        }
      }
    });

    web.setWebViewClient(new WebViewClient() {
      @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        if (!request.isForMainFrame()) return false;
        Uri destination = request.getUrl();
        String url = destination.toString();
        if (WebHostPolicy.isTrustedHttps(url)) return false;
        if (!WebHostPolicy.canOpenExternally(url)) return true;
        try {
          startActivity(new Intent(Intent.ACTION_VIEW, destination));
        } catch (ActivityNotFoundException | SecurityException exception) {
          Toast.makeText(MainActivity.this, getString(R.string.open_failed), Toast.LENGTH_SHORT).show();
        }
        return true;
      }
    });

    if (state == null || web.restoreState(state) == null) web.loadUrl(HOME);
  }

  private void showPrivacyAndAccountOptions() {
    new AlertDialog.Builder(this)
        .setTitle(R.string.account_dialog_title)
        .setItems(new String[]{getString(R.string.privacy_action), getString(R.string.deletion_action)}, (dialog, which) ->
            openAccountPage(which == 0 ? PRIVACY_URL : DELETE_ACCOUNT_URL))
        .setNegativeButton(R.string.cancel, null)
        .show();
  }

  private void openAccountPage(String url) {
    if (!WebHostPolicy.isTrustedHttps(url)) {
      Toast.makeText(this, getString(R.string.link_unavailable), Toast.LENGTH_SHORT).show();
      return;
    }
    try {
      Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
      intent.addCategory(Intent.CATEGORY_BROWSABLE);
      startActivity(intent);
    } catch (ActivityNotFoundException | SecurityException exception) {
      Toast.makeText(this, getString(R.string.open_failed), Toast.LENGTH_LONG).show();
    }
  }

  private void handleWebPermission(PermissionRequest request) {
    String[] resources = request.getResources();
    // Only the intended first-party HTTPS app may request microphone capture.
    // Camera, location, and other resource requests are never auto-granted.
    if (!WebHostPolicy.isTrustedHttps(request.getOrigin().toString())
        || resources.length != 1
        || !PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resources[0])
        || web == null
        || !WebHostPolicy.isTrustedHttps(web.getUrl())) {
      request.deny();
      return;
    }
    if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
      request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
      return;
    }
    if (pendingAudioPermission != null) pendingAudioPermission.deny();
    pendingAudioPermission = request;
    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MICROPHONE);
  }

  @Override public void onRequestPermissionsResult(
      int requestCode, String[] permissions, int[] grantResults) {
    super.onRequestPermissionsResult(requestCode, permissions, grantResults);
    if (requestCode != REQUEST_MICROPHONE || pendingAudioPermission == null) return;
    PermissionRequest request = pendingAudioPermission;
    pendingAudioPermission = null;
    if (grantResults.length == 1
        && grantResults[0] == PackageManager.PERMISSION_GRANTED
        && WebHostPolicy.isTrustedHttps(request.getOrigin().toString())
        && web != null && WebHostPolicy.isTrustedHttps(web.getUrl())) {
      request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
    } else {
      request.deny();
      Toast.makeText(this, getString(R.string.microphone_fallback), Toast.LENGTH_LONG).show();
    }
  }

  @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
    super.onActivityResult(requestCode, resultCode, data);
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
    if (pendingAudioPermission != null) {
      pendingAudioPermission.deny();
      pendingAudioPermission = null;
    }
    if (pendingFiles != null) {
      pendingFiles.onReceiveValue(null);
      pendingFiles = null;
    }
    if (web != null) {
      web.destroy();
      web = null;
    }
    super.onDestroy();
  }
}
