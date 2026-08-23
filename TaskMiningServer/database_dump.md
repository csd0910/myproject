# 📊 PostgreSQL Database Dump
Generated at: 2026-08-08 08:43:28 (Japan Time)

## 🏢 `employees` Table
### Schema
| Column Name | Data Type |
|---|---|
| id | integer |
| user_id | character varying |
| name | character varying |
| department | character varying |
| section | character varying |
| registered_at | double precision |

### Data
| id | user_id | name | department | section | registered_at |
| --- | --- | --- | --- | --- | --- |
| 5 | user-111 | 山田 太郎 | 営業部 | 営業課 | 2026-08-07 19:22:23 |
| 6 | user-222 | 佐藤 花子 | システム部 | システム課 | 2026-08-07 19:22:23 |
| 7 | user-333 | 鈴木 一郎 | 商品部 | 商品課 | 2026-08-07 19:22:23 |
| 11 | user-444 | 伊藤 健人 | システム部 | システム運営課 | 2026-08-07 19:23:16 |
| 12 | user-555 | テスト 五郎 | 業務改革室 | - | 2026-08-07 19:23:16 |
| 13 | user-666 | テスト 六郎 | Eコマース部 | Eコマース課 | 2026-08-07 19:23:16 |
| 2 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | 伊藤健人 | システム部 | システム運営課 | 2026-08-07 17:55:08 |

## 📋 `client_logs` Table (Latest 100 entries)
### Schema
| Column Name | Data Type |
|---|---|
| id | integer |
| user_id | character varying |
| app_name | character varying |
| folder_name | text |
| file_name | text |
| operation_type | character varying |
| manual_typing_count | integer |
| manual_typing_time | integer |
| copy_paste_count | integer |
| duration_seconds | integer |
| idle_time_seconds | integer |
| context_switch_count | integer |
| cpu_usage_percent | double precision |
| memory_usage_mb | double precision |
| browser_tab_count | integer |
| is_processed | integer |
| received_at | double precision |
| click_count | integer |
| scroll_count | integer |
| mouse_distance | integer |

### Data
| id | user_id | app_name | folder_name | file_name | operation_type | manual_typing_count | manual_typing_time | copy_paste_count | duration_seconds | idle_time_seconds | context_switch_count | cpu_usage_percent | memory_usage_mb | browser_tab_count | is_processed | received_at | click_count | scroll_count | mouse_distance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 27908 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:43:20 | 0 | 0 | 0 |
| 27907 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:43:19 | 0 | 0 | 0 |
| 27906 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:43:09 | 0 | 0 | 0 |
| 27905 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | explorer.exe |  |  | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:43:09 | 0 | 0 | 0 |
| 27904 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | explorer.exe |  |  | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:59 | 0 | 0 | 0 |
| 27903 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:58 | 0 | 0 | 0 |
| 27902 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:48 | 0 | 0 | 0 |
| 27901 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:48 | 0 | 0 | 0 |
| 27900 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:38 | 0 | 0 | 0 |
| 27899 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:37 | 0 | 0 | 0 |
| 27898 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:27 | 0 | 0 | 0 |
| 27897 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:27 | 0 | 0 | 0 |
| 27896 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:27 | 0 | 0 | 0 |
| 27895 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:16 | 0 | 0 | 0 |
| 27894 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:16 | 0 | 0 | 0 |
| 27893 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:06 | 0 | 0 | 0 |
| 27892 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:42:06 | 0 | 0 | 0 |
| 27891 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:55 | 0 | 0 | 0 |
| 27890 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:55 | 0 | 0 | 0 |
| 27889 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:45 | 0 | 0 | 0 |
| 27888 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:45 | 0 | 0 | 0 |
| 27887 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:34 | 0 | 0 | 0 |
| 27886 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:34 | 0 | 0 | 0 |
| 27885 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:24 | 0 | 0 | 0 |
| 27884 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:23 | 0 | 0 | 0 |
| 27883 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:13 | 0 | 0 | 0 |
| 27882 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:13 | 0 | 0 | 0 |
| 27881 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:03 | 0 | 0 | 0 |
| 27880 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:41:02 | 0 | 0 | 0 |
| 27879 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:52 | 0 | 0 | 0 |
| 27878 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:52 | 0 | 0 | 0 |
| 27877 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:42 | 0 | 0 | 0 |
| 27876 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:41 | 0 | 0 | 0 |
| 27875 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:31 | 0 | 0 | 0 |
| 27874 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:31 | 0 | 0 | 0 |
| 27873 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | Antigravity IDE.exe |  | Antigravity IDE | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:31 | 0 | 0 | 0 |
| 27872 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:20 | 0 | 0 | 0 |
| 27871 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:20 | 0 | 0 | 0 |
| 27870 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | chrome.exe |  | 詳細DX抽出レポート - 20260727 (ミクロビュー) - Google Chrome | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:10 | 0 | 0 | 0 |
| 27869 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | remoting_desktop.exe |  |  | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:40:10 | 0 | 0 | 0 |
| 27868 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | remoting_desktop.exe |  |  | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:59 | 0 | 0 | 0 |
| 27867 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | remoting_desktop.exe |  |  | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:59 | 0 | 0 | 0 |
| 27866 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:49 | 0 | 0 | 0 |
| 27865 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:48 | 0 | 0 | 0 |
| 27864 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:38 | 0 | 0 | 0 |
| 27863 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:38 | 0 | 0 | 0 |
| 27862 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:28 | 0 | 0 | 0 |
| 27861 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:27 | 0 | 0 | 0 |
| 27860 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:17 | 0 | 0 | 0 |
| 27859 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:17 | 0 | 0 | 0 |
| 27858 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:06 | 0 | 0 | 0 |
| 27857 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:39:06 | 0 | 0 | 0 |
| 27856 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:56 | 0 | 0 | 0 |
| 27855 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:55 | 0 | 0 | 0 |
| 27854 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:55 | 0 | 0 | 0 |
| 27853 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:45 | 0 | 0 | 0 |
| 27852 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:44 | 0 | 0 | 0 |
| 27851 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:34 | 0 | 0 | 0 |
| 27850 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:34 | 0 | 0 | 0 |
| 27849 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:24 | 0 | 0 | 0 |
| 27848 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:23 | 0 | 0 | 0 |
| 27847 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:13 | 0 | 0 | 0 |
| 27846 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:13 | 0 | 0 | 0 |
| 27845 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:02 | 0 | 0 | 0 |
| 27844 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:38:02 | 0 | 0 | 0 |
| 27843 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:52 | 0 | 0 | 0 |
| 27842 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:52 | 0 | 0 | 0 |
| 27841 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:41 | 0 | 0 | 0 |
| 27840 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:41 | 0 | 0 | 0 |
| 27839 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:31 | 0 | 0 | 0 |
| 27838 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:30 | 0 | 0 | 0 |
| 27837 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:20 | 0 | 0 | 0 |
| 27836 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:20 | 0 | 0 | 0 |
| 27835 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:19 | 0 | 0 | 0 |
| 27834 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:09 | 0 | 0 | 0 |
| 27833 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:37:09 | 0 | 0 | 0 |
| 27832 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:58 | 0 | 0 | 0 |
| 27831 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:58 | 0 | 0 | 0 |
| 27830 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:48 | 0 | 0 | 0 |
| 27829 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:47 | 0 | 0 | 0 |
| 27828 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:37 | 0 | 0 | 0 |
| 27827 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:37 | 0 | 0 | 0 |
| 27826 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:26 | 0 | 0 | 0 |
| 27825 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:26 | 0 | 0 | 0 |
| 27824 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:16 | 0 | 0 | 0 |
| 27823 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:16 | 0 | 0 | 0 |
| 27822 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:05 | 0 | 0 | 0 |
| 27821 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:36:05 | 0 | 0 | 0 |
| 27820 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:55 | 0 | 0 | 0 |
| 27819 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:54 | 0 | 0 | 0 |
| 27818 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:44 | 0 | 0 | 0 |
| 27817 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:44 | 0 | 0 | 0 |
| 27816 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:43 | 0 | 0 | 0 |
| 27815 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:33 | 0 | 0 | 0 |
| 27814 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:33 | 0 | 0 | 0 |
| 27813 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:22 | 0 | 0 | 0 |
| 27812 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:22 | 0 | 0 | 0 |
| 27811 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:12 | 0 | 0 | 0 |
| 27810 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:12 | 0 | 0 | 0 |
| 27809 | ea8b1d32-6645-4ae3-8ca7-276260105c75 | LockApp.exe |  | Windows の既定のロック画面 | macro | 0 | 0 | 0 | 5 | 0 | 0 | 0.0 | 0.0 | 0 | 0 | 2026-08-08 08:35:01 | 0 | 0 | 0 |