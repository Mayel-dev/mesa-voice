#pragma once
// Public dummy values make the complete Wi-Fi/audio path linkable in validation.
// They are not user credentials. Never deploy this configuration.
constexpr char WIFI_SSID[] = "MESA-VALIDATION-DO-NOT-USE";
constexpr char WIFI_PASSWORD[] = "NotARealNetworkPassword";
constexpr char SERVER_HOST[] = "192.0.2.1"; // TEST-NET-1 documentation address
constexpr unsigned short SERVER_PORT = 8000;
constexpr char API_TOKEN[] = "validation-token-public-do-not-deploy";
