Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Get-KittingInput {
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Windowsキッティング入力フォーム"
    $form.Size = New-Object System.Drawing.Size(400, 450)
    $form.StartPosition = "CenterScreen"; $form.FormBorderStyle = "FixedDialog"; $form.MaximizeBox = $false
    $form.Font = New-Object System.Drawing.Font("Meiryo UI", 9)

    $y = 20
    function Add-Field($label, $default, $yy) {
        $lbl = New-Object System.Windows.Forms.Label; $lbl.Text = $label; $lbl.Location = New-Object System.Drawing.Point(20, $yy); $lbl.AutoSize = $true
        $form.Controls.Add($lbl)
        $txt = New-Object System.Windows.Forms.TextBox; $txt.Location = New-Object System.Drawing.Point(150, $yy); $txt.Width = 200; $txt.Text = $default
        $form.Controls.Add($txt); return $txt
    }

    $txtPC = Add-Field "コンピューター名:" $env:COMPUTERNAME $y; $y += 40
    $chkIP = New-Object System.Windows.Forms.CheckBox; $chkIP.Text = "固定IPを設定する"; $chkIP.Location = New-Object System.Drawing.Point(20, $y); $chkIP.AutoSize = $true; $form.Controls.Add($chkIP); $y += 40
    $txtIP = Add-Field "IPアドレス:" "10.85.33.100" $y; $y += 40
    $txtSubnet = Add-Field "サブネットマスク:" "255.255.254.0" $y; $y += 40
    $txtGW = Add-Field "ゲートウェイ:" "10.85.33.254" $y; $y += 40
    $txtDNS1 = Add-Field "DNS1:" "1.1.1.1" $y; $y += 40
    $txtDNS2 = Add-Field "DNS2:" "8.8.8.8" $y; $y += 40

    $btnOK = New-Object System.Windows.Forms.Button; $btnOK.Text = "開始"; $btnOK.DialogResult = [System.Windows.Forms.DialogResult]::OK; $btnOK.Location = New-Object System.Drawing.Point(130, ($y + 20)); $form.Controls.Add($btnOK); $form.AcceptButton = $btnOK

    if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return @{ ComputerName = $txtPC.Text; StaticIP = $chkIP.Checked; IPAddress = $txtIP.Text; SubnetMask = $txtSubnet.Text; Gateway = $txtGW.Text; DNS1 = $txtDNS1.Text; DNS2 = $txtDNS2.Text }
    }
    return $null
}
