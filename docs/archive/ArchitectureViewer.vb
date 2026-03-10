Imports System.Net.Http
Imports System.Text.Json
Imports System.Text

''' <summary>
''' 乾坤測繪公文管理系統架構檢視器 - VB.NET版本
''' 用於檢視Python後端與JavaScript前端的對應關係
''' </summary>
Module ArchitectureViewer
    Private ReadOnly client As New HttpClient()
    Private Const API_BASE As String = "http://localhost:8001"

    Sub Main()
        Console.WriteLine("=" * 60)
        Console.WriteLine("🏢 乾坤測繪公文管理系統架構檢視器")
        Console.WriteLine("=" * 60)

        Try
            ' 檢查系統狀態
            CheckSystemStatus().Wait()
            
            ' 顯示架構對應關係
            ShowArchitectureMapping()
            
            ' 互動式功能測試
            InteractiveMenu()
            
        Catch ex As Exception
            Console.WriteLine($"❌ 系統錯誤: {ex.Message}")
        End Try

        Console.WriteLine("按任意鍵結束...")
        Console.ReadKey()
    End Sub

    ''' <summary>
    ''' 檢查系統狀態
    ''' </summary>
    Async Function CheckSystemStatus() As Task
        Console.WriteLine("📡 正在檢查系統狀態...")
        
        Try
            ' 檢查後端健康狀態
            Dim healthResponse = Await client.GetAsync($"{API_BASE}/health")
            If healthResponse.IsSuccessStatusCode Then
                Console.WriteLine("✅ 後端服務 (Python FastAPI): 正常運行")
            Else
                Console.WriteLine("❌ 後端服務: 無法連接")
            End If

            ' 檢查前端服務 (通常在3005或3006端口)
            Dim frontendPorts = {3005, 3006}
            Dim frontendRunning = False
            
            For Each port In frontendPorts
                Try
                    Dim frontendResponse = Await client.GetAsync($"http://localhost:{port}")
                    If frontendResponse.IsSuccessStatusCode Then
                        Console.WriteLine($"✅ 前端服務 (React): 運行在端口 {port}")
                        frontendRunning = True
                        Exit For
                    End If
                Catch
                    ' 忽略連接錯誤，繼續檢查下一個端口
                End Try
            Next
            
            If Not frontendRunning Then
                Console.WriteLine("❌ 前端服務: 未檢測到運行中的服務")
            End If

        Catch ex As Exception
            Console.WriteLine($"❌ 系統檢查失敗: {ex.Message}")
        End Try
        
        Console.WriteLine()
    End Function

    ''' <summary>
    ''' 顯示架構對應關係
    ''' </summary>
    Sub ShowArchitectureMapping()
        Console.WriteLine("🗂️ 前端-後端檔案對應關係:")
        Console.WriteLine("-" * 80)
        
        Dim mappings = {
            ("前端API服務", "frontend/src/services/documentAPI.js", "後端API端點", "backend/app/api/endpoints/documents.py"),
            ("CSV匯入介面", "frontend/src/components/Documents/DocumentImport.jsx", "CSV處理器", "backend/csv_processor.py"),
            ("API配置", "frontend/src/api/config.ts", "主應用程式", "backend/main.py"),
            ("文件API", "frontend/src/api/documents.ts", "資料庫模型", "backend/app/db/models.py")
        }

        For Each mapping In mappings
            Console.WriteLine($"📁 {mapping.Item1,-15} | {mapping.Item2}")
            Console.WriteLine($"   {mapping.Item3,-15} | {mapping.Item4}")
            Console.WriteLine()
        Next
    End Sub

    ''' <summary>
    ''' 互動式功能選單
    ''' </summary>
    Sub InteractiveMenu()
        Console.WriteLine("🔧 互動式功能測試:")
        Console.WriteLine("1. 測試文件列表API")
        Console.WriteLine("2. 測試健康檢查API") 
        Console.WriteLine("3. 顯示API端點清單")
        Console.WriteLine("4. 測試資料庫連接")
        Console.WriteLine("5. 退出")
        Console.WriteLine()

        While True
            Console.Write("請選擇功能 (1-5): ")
            Dim choice = Console.ReadLine()

            Select Case choice
                Case "1"
                    TestDocumentsAPI().Wait()
                Case "2"
                    TestHealthAPI().Wait()
                Case "3"
                    ShowAPIEndpoints()
                Case "4"
                    TestDatabaseConnection().Wait()
                Case "5"
                    Exit While
                Case Else
                    Console.WriteLine("❌ 無效選擇，請輸入1-5")
            End Select
            
            Console.WriteLine()
        End While
    End Sub

    ''' <summary>
    ''' 測試文件列表API
    ''' </summary>
    Async Function TestDocumentsAPI() As Task
        Console.WriteLine("📋 測試文件列表API...")
        
        Try
            Dim response = Await client.GetAsync($"{API_BASE}/api/documents/?limit=3")
            Dim content = Await response.Content.ReadAsStringAsync()
            
            If response.IsSuccessStatusCode Then
                Console.WriteLine("✅ API調用成功")
                
                ' 解析JSON並顯示結果
                Dim jsonDoc = JsonDocument.Parse(content)
                If jsonDoc.RootElement.TryGetProperty("documents", out var docs) Then
                    Console.WriteLine($"📄 找到 {docs.GetArrayLength()} 筆文件")
                    
                    For Each doc In docs.EnumerateArray().Take(3)
                        If doc.TryGetProperty("doc_number", out var docNum) AndAlso
                           doc.TryGetProperty("subject", out var subject) Then
                            Console.WriteLine($"   • {docNum.GetString()}: {subject.GetString()}")
                        End If
                    Next
                End If
            Else
                Console.WriteLine($"❌ API調用失敗: {response.StatusCode}")
                Console.WriteLine($"回應內容: {content}")
            End If
            
        Catch ex As Exception
            Console.WriteLine($"❌ 測試失敗: {ex.Message}")
        End Try
    End Function

    ''' <summary>
    ''' 測試健康檢查API
    ''' </summary>
    Async Function TestHealthAPI() As Task
        Console.WriteLine("🔍 測試健康檢查API...")
        
        Try
            Dim response = Await client.GetAsync($"{API_BASE}/health")
            Dim content = Await response.Content.ReadAsStringAsync()
            
            If response.IsSuccessStatusCode Then
                Console.WriteLine("✅ 健康檢查通過")
                Console.WriteLine($"回應: {content}")
            Else
                Console.WriteLine($"❌ 健康檢查失敗: {response.StatusCode}")
            End If
            
        Catch ex As Exception
            Console.WriteLine($"❌ 測試失敗: {ex.Message}")
        End Try
    End Function

    ''' <summary>
    ''' 顯示API端點清單
    ''' </summary>
    Sub ShowAPIEndpoints()
        Console.WriteLine("📡 主要API端點清單:")
        Console.WriteLine("-" * 60)
        
        Dim endpoints = {
            ("GET", "/api/documents/", "取得文件列表"),
            ("POST", "/api/documents/", "建立新文件"),
            ("GET", "/api/documents/{id}", "取得特定文件"),
            ("PUT", "/api/documents/{id}", "更新文件"),
            ("DELETE", "/api/documents/{id}", "刪除文件"),
            ("POST", "/api/documents/import", "CSV匯入"),
            ("GET", "/api/documents/export/download", "匯出Excel"),
            ("GET", "/health", "健康檢查")
        }

        For Each endpoint In endpoints
            Console.WriteLine($"{endpoint.Item1,-6} | {endpoint.Item2,-30} | {endpoint.Item3}")
        Next
    End Sub

    ''' <summary>
    ''' 測試資料庫連接
    ''' </summary>
    Async Function TestDatabaseConnection() As Task
        Console.WriteLine("🗄️ 測試資料庫連接...")
        
        Try
            ' 透過API測試資料庫
            Dim response = Await client.GetAsync($"{API_BASE}/api/documents/?limit=1")
            
            If response.IsSuccessStatusCode Then
                Console.WriteLine("✅ 資料庫連接正常")
                
                Dim content = Await response.Content.ReadAsStringAsync()
                Dim jsonDoc = JsonDocument.Parse(content)
                
                If jsonDoc.RootElement.TryGetProperty("total", out var total) Then
                    Console.WriteLine($"📊 資料庫中共有 {total.GetInt32()} 筆文件記錄")
                End If
            Else
                Console.WriteLine("❌ 資料庫連接可能有問題")
            End If
            
        Catch ex As Exception
            Console.WriteLine($"❌ 資料庫測試失敗: {ex.Message}")
        End Try
    End Function

End Module