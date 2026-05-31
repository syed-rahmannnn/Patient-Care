import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'api/client.dart';
import 'auth/auth_service.dart';
import 'auth/login_screen.dart';
import 'beds/beds_screen.dart';
import 'fcm/fcm_setup.dart';

// Default backend URL. Override at runtime with:
//   flutter run --dart-define=BACKEND_URL=http://<lan-ip>:8000
const String kBackendUrl = String.fromEnvironment(
  'BACKEND_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();

  // A server URL the user saved in-app overrides the compile-time default.
  final savedUrl = await ApiClient.loadSavedServerUrl();
  final api = ApiClient(baseUrl: savedUrl ?? kBackendUrl);
  final auth = AuthService(api);
  await auth.bootstrap();
  await initFcm(api: api);

  runApp(MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: api),
      ChangeNotifierProvider<AuthService>.value(value: auth),
    ],
    child: const PatientCareApp(),
  ));
}

class PatientCareApp extends StatelessWidget {
  const PatientCareApp({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF00897B),
      brightness: Brightness.light,
    );
    return MaterialApp(
      title: 'Patient Care',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: scheme,
        useMaterial3: true,
        scaffoldBackgroundColor: scheme.surfaceContainerLowest,
        appBarTheme: AppBarTheme(
          backgroundColor: scheme.surface,
          surfaceTintColor: Colors.transparent,
          elevation: 0,
          centerTitle: false,
          titleTextStyle: TextStyle(
            color: scheme.onSurface,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
        cardTheme: CardThemeData(
          color: scheme.surfaceContainer,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
        floatingActionButtonTheme: FloatingActionButtonThemeData(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
      ),
      home: Consumer<AuthService>(
        builder: (_, auth, __) => auth.signedIn ? const BedsScreen() : const LoginScreen(),
      ),
    );
  }
}
