param(
    [string]$Python = "python",
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

$RepoRoot = Split-Path -Parent $PSScriptRoot

$PackageInitPath = Join-Path `
    $RepoRoot `
    "documents_organizer\__init__.py"

$PyProjectPath = Join-Path `
    $RepoRoot `
    "pyproject.toml"

$VersionInfoPath = Join-Path `
    $RepoRoot `
    "packaging\windows\version_info.txt"

$SpecPath = Join-Path `
    $RepoRoot `
    "DocumentsOrganizer.spec"

$BuildDirectory = Join-Path `
    $RepoRoot `
    "build"

$DistDirectory = Join-Path `
    $RepoRoot `
    "dist"

$ApplicationDirectory = Join-Path `
    $DistDirectory `
    "DocumentsOrganizer"

$ExecutablePath = Join-Path `
    $ApplicationDirectory `
    "DocumentsOrganizer.exe"

$ArtifactsDirectory = Join-Path `
    $RepoRoot `
    "artifacts"


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

function Write-Step {
    param(
        [string]$Message
    )

    Write-Host ""
    Write-Host "============================================================"
    Write-Host $Message
    Write-Host "============================================================"
}


function Invoke-Python {
    param(
        [string[]]$Arguments
    )

    & $Python @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Python command failed with exit code " +
            "$LASTEXITCODE."
        )
    }
}


function Get-RegexValue {
    param(
        [string]$Path,
        [string]$Pattern,
        [string]$Description
    )

    if (-not (Test-Path $Path)) {
        throw "Required file not found: $Path"
    }

    $Content = Get-Content `
        $Path `
        -Raw

    $Match = [regex]::Match(
        $Content,
        $Pattern
    )

    if (-not $Match.Success) {
        throw (
            "Unable to determine $Description " +
            "from $Path."
        )
    }

    return $Match.Groups[1].Value
}


function Get-WindowsFixedVersion {
    param(
        [string]$Path,
        [string]$FieldName
    )

    if (-not (Test-Path $Path)) {
        throw "Required file not found: $Path"
    }

    $Content = Get-Content `
        $Path `
        -Raw

    $EscapedFieldName = (
        [regex]::Escape(
            $FieldName
        )
    )

    $Pattern = (
        $EscapedFieldName +
        '\s*=\s*\(' +
        '\s*(\d+)\s*,' +
        '\s*(\d+)\s*,' +
        '\s*(\d+)\s*,' +
        '\s*(\d+)\s*' +
        '\)'
    )

    $Match = [regex]::Match(
        $Content,
        $Pattern
    )

    if (-not $Match.Success) {
        throw (
            "Unable to determine Windows " +
            "$FieldName from $Path."
        )
    }

    return (
        $Match.Groups[1].Value +
        "." +
        $Match.Groups[2].Value +
        "." +
        $Match.Groups[3].Value +
        "." +
        $Match.Groups[4].Value
    )
}


# -----------------------------------------------------------------------------
# Environment validation
# -----------------------------------------------------------------------------

Write-Step "Validating build environment"

if ($env:OS -ne "Windows_NT") {
    throw (
        "Windows release builds must be created on Windows."
    )
}

if (-not [Environment]::Is64BitProcess) {
    throw (
        "Documents Organizer Windows releases must be built " +
        "using a 64-bit Python environment."
    )
}

Push-Location $RepoRoot

try {
    & $Python --version

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Unable to execute Python using '$Python'."
        )
    }

    Write-Host ""
    Write-Host "Repository:"
    Write-Host "  $RepoRoot"


    # -------------------------------------------------------------------------
    # Application version
    # -------------------------------------------------------------------------

    Write-Step "Validating application version"

    $PackageVersion = Get-RegexValue `
        -Path $PackageInitPath `
        -Pattern '__version__\s*=\s*"([^"]+)"' `
        -Description "package version"

    $ProjectVersion = Get-RegexValue `
        -Path $PyProjectPath `
        -Pattern '(?m)^version\s*=\s*"([^"]+)"' `
        -Description "pyproject version"

    if ($PackageVersion -ne $ProjectVersion) {
        throw (
            "Application version mismatch detected.`n" +
            "Package version:   $PackageVersion`n" +
            "pyproject version: $ProjectVersion"
        )
    }

    $Version = $PackageVersion


    # -------------------------------------------------------------------------
    # Release and Windows version calculation
    # -------------------------------------------------------------------------

    $ReleaseVersion = $Version

    $VersionMajor = $null
    $VersionMinor = $null
    $VersionPatch = $null
    $VersionBuild = $null

    if (
        $Version -match
        '^(\d+)\.(\d+)\.(\d+)rc(\d+)$'
    ) {
        $VersionMajor = [int]$Matches[1]
        $VersionMinor = [int]$Matches[2]
        $VersionPatch = [int]$Matches[3]
        $VersionBuild = [int]$Matches[4]

        $ReleaseVersion = (
            "$VersionMajor." +
            "$VersionMinor." +
            "$VersionPatch" +
            "-rc" +
            "$VersionBuild"
        )
    }
    elseif (
        $Version -match
        '^(\d+)\.(\d+)\.(\d+)$'
    ) {
        $VersionMajor = [int]$Matches[1]
        $VersionMinor = [int]$Matches[2]
        $VersionPatch = [int]$Matches[3]
        $VersionBuild = 0
    }
    else {
        throw (
            "Unsupported application version format: $Version`n" +
            "Expected a version such as 0.2.0 or 0.2.0rc1."
        )
    }

    $ExpectedWindowsVersion = (
        "$VersionMajor." +
        "$VersionMinor." +
        "$VersionPatch." +
        "$VersionBuild"
    )

    Write-Host "Application version:"
    Write-Host "  $Version"

    Write-Host "Release version:"
    Write-Host "  $ReleaseVersion"

    Write-Host "Expected Windows version:"
    Write-Host "  $ExpectedWindowsVersion"


    # -------------------------------------------------------------------------
    # Windows source metadata validation
    # -------------------------------------------------------------------------

    Write-Step "Validating Windows version metadata"

    $WindowsProductVersion = Get-RegexValue `
        -Path $VersionInfoPath `
        -Pattern (
            '(?s)StringStruct\(' +
            '\s*"ProductVersion",' +
            '\s*"([^"]+)"'
        ) `
        -Description "Windows ProductVersion"

    $WindowsFileVersion = Get-RegexValue `
        -Path $VersionInfoPath `
        -Pattern (
            '(?s)StringStruct\(' +
            '\s*"FileVersion",' +
            '\s*"([^"]+)"'
        ) `
        -Description "Windows FileVersion"

    $WindowsFixedFileVersion = Get-WindowsFixedVersion `
        -Path $VersionInfoPath `
        -FieldName "filevers"

    $WindowsFixedProductVersion = Get-WindowsFixedVersion `
        -Path $VersionInfoPath `
        -FieldName "prodvers"

    Write-Host "ProductVersion string:"
    Write-Host "  $WindowsProductVersion"

    Write-Host "FileVersion string:"
    Write-Host "  $WindowsFileVersion"

    Write-Host "Fixed filevers:"
    Write-Host "  $WindowsFixedFileVersion"

    Write-Host "Fixed prodvers:"
    Write-Host "  $WindowsFixedProductVersion"

    if (
        $WindowsProductVersion -ne
        $Version
    ) {
        throw (
            "Windows ProductVersion does not match " +
            "the application version.`n" +
            "Expected: $Version`n" +
            "Actual:   $WindowsProductVersion"
        )
    }

    if (
        $WindowsFileVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "Windows FileVersion string does not match " +
            "the expected numeric Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $WindowsFileVersion"
        )
    }

    if (
        $WindowsFixedFileVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "FixedFileInfo filevers does not match " +
            "the expected Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $WindowsFixedFileVersion"
        )
    }

    if (
        $WindowsFixedProductVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "FixedFileInfo prodvers does not match " +
            "the expected Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $WindowsFixedProductVersion"
        )
    }

    Write-Host ""
    Write-Host "Windows source metadata is consistent."


    # -------------------------------------------------------------------------
    # Git information
    # -------------------------------------------------------------------------

    Write-Step "Checking repository state"

    $GitCommit = (
        git rev-parse --short HEAD
    ).Trim()

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the Git commit."
    }

    Write-Host "Git commit:"
    Write-Host "  $GitCommit"

    $GitStatus = git status --porcelain

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine Git repository status."
    }

    if ($GitStatus) {
        Write-Warning (
            "The working tree contains uncommitted changes. " +
            "The build can continue, but official release " +
            "candidates should normally be built from a clean tree."
        )
    }
    else {
        Write-Host "Working tree is clean."
    }


    # -------------------------------------------------------------------------
    # Compile validation
    # -------------------------------------------------------------------------

    Write-Step "Compile-checking application"

    Invoke-Python -Arguments @(
        "-m",
        "compileall",
        "main.py",
        "documents_organizer"
    )


    # -------------------------------------------------------------------------
    # Automated tests
    # -------------------------------------------------------------------------

    if (-not $SkipTests) {
        Write-Step "Running automated tests"

        Invoke-Python -Arguments @(
            "-m",
            "pytest"
        )
    }
    else {
        Write-Warning "Automated tests were skipped."
    }


    # -------------------------------------------------------------------------
    # Clean previous PyInstaller output
    # -------------------------------------------------------------------------

    Write-Step "Cleaning previous build output"

    if (Test-Path $BuildDirectory) {
        Remove-Item `
            $BuildDirectory `
            -Recurse `
            -Force
    }

    if (Test-Path $DistDirectory) {
        Remove-Item `
            $DistDirectory `
            -Recurse `
            -Force
    }

    Write-Host "Previous build output removed."


    # -------------------------------------------------------------------------
    # PyInstaller
    # -------------------------------------------------------------------------

    Write-Step "Building Documents Organizer v$ReleaseVersion"

    Invoke-Python -Arguments @(
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        $SpecPath
    )

    if (-not (Test-Path $ExecutablePath)) {
        throw (
            "PyInstaller completed but the expected executable " +
            "was not found:`n$ExecutablePath"
        )
    }

    Write-Host ""
    Write-Host "Executable created:"
    Write-Host "  $ExecutablePath"


    # -------------------------------------------------------------------------
    # Executable metadata validation
    # -------------------------------------------------------------------------

    Write-Step "Validating Windows executable metadata"

    $ExecutableVersion = (
        Get-Item $ExecutablePath
    ).VersionInfo

    $ExecutableFixedFileVersion = (
        "$($ExecutableVersion.FileMajorPart)." +
        "$($ExecutableVersion.FileMinorPart)." +
        "$($ExecutableVersion.FileBuildPart)." +
        "$($ExecutableVersion.FilePrivatePart)"
    )

    $ExecutableFixedProductVersion = (
        "$($ExecutableVersion.ProductMajorPart)." +
        "$($ExecutableVersion.ProductMinorPart)." +
        "$($ExecutableVersion.ProductBuildPart)." +
        "$($ExecutableVersion.ProductPrivatePart)"
    )

    Write-Host "File description:"
    Write-Host (
        "  " +
        $ExecutableVersion.FileDescription
    )

    Write-Host "FileVersion string:"
    Write-Host (
        "  " +
        $ExecutableVersion.FileVersion
    )

    Write-Host "Fixed FileVersion:"
    Write-Host (
        "  " +
        $ExecutableFixedFileVersion
    )

    Write-Host "ProductVersion string:"
    Write-Host (
        "  " +
        $ExecutableVersion.ProductVersion
    )

    Write-Host "Fixed ProductVersion:"
    Write-Host (
        "  " +
        $ExecutableFixedProductVersion
    )

    if (
        $ExecutableVersion.ProductName -ne
        "Documents Organizer"
    ) {
        throw (
            "Unexpected ProductName in Windows executable.`n" +
            "Expected: Documents Organizer`n" +
            "Actual:   $($ExecutableVersion.ProductName)"
        )
    }

    if (
        $ExecutableVersion.FileDescription -ne
        "Documents Organizer"
    ) {
        throw (
            "Unexpected FileDescription in Windows executable.`n" +
            "Expected: Documents Organizer`n" +
            "Actual:   $($ExecutableVersion.FileDescription)"
        )
    }

    if (
        $ExecutableVersion.ProductVersion -ne
        $Version
    ) {
        throw (
            "Executable ProductVersion string does not match " +
            "the application version.`n" +
            "Expected: $Version`n" +
            "Actual:   $($ExecutableVersion.ProductVersion)"
        )
    }

    if (
        $ExecutableVersion.FileVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "Executable FileVersion string does not match " +
            "the expected Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $($ExecutableVersion.FileVersion)"
        )
    }

    if (
        $ExecutableFixedFileVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "Executable fixed FileVersion does not match " +
            "the expected Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $ExecutableFixedFileVersion"
        )
    }

    if (
        $ExecutableFixedProductVersion -ne
        $ExpectedWindowsVersion
    ) {
        throw (
            "Executable fixed ProductVersion does not match " +
            "the expected Windows version.`n" +
            "Expected: $ExpectedWindowsVersion`n" +
            "Actual:   $ExecutableFixedProductVersion"
        )
    }

    Write-Host ""
    Write-Host "Executable metadata is valid."


    # -------------------------------------------------------------------------
    # Release artifact
    # -------------------------------------------------------------------------

    Write-Step "Creating release artifact"

    if (-not (Test-Path $ArtifactsDirectory)) {
        New-Item `
            -ItemType Directory `
            -Path $ArtifactsDirectory `
            | Out-Null
    }

    $ArtifactName = (
        "DocumentsOrganizer-v" +
        $ReleaseVersion +
        "-windows-x64"
    )

    $StagingDirectory = Join-Path `
        $ArtifactsDirectory `
        $ArtifactName

    $ZipPath = Join-Path `
        $ArtifactsDirectory `
        ($ArtifactName + ".zip")

    $HashPath = (
        $ZipPath +
        ".sha256.txt"
    )

    if (Test-Path $StagingDirectory) {
        Remove-Item `
            $StagingDirectory `
            -Recurse `
            -Force
    }

    if (Test-Path $ZipPath) {
        Remove-Item `
            $ZipPath `
            -Force
    }

    if (Test-Path $HashPath) {
        Remove-Item `
            $HashPath `
            -Force
    }

    New-Item `
        -ItemType Directory `
        -Path $StagingDirectory `
        | Out-Null

    Copy-Item `
        -Path $ApplicationDirectory `
        -Destination $StagingDirectory `
        -Recurse

    Add-Type `
        -AssemblyName System.IO.Compression.FileSystem

    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $StagingDirectory,
        $ZipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    Remove-Item `
        $StagingDirectory `
        -Recurse `
        -Force

    if (-not (Test-Path $ZipPath)) {
        throw (
            "Release ZIP was not created successfully."
        )
    }


    # -------------------------------------------------------------------------
    # SHA-256
    # -------------------------------------------------------------------------

    Write-Step "Calculating SHA-256 checksum"

    $Hash = Get-FileHash `
        $ZipPath `
        -Algorithm SHA256

    $HashText = (
        $Hash.Hash.ToLowerInvariant() +
        "  " +
        [System.IO.Path]::GetFileName(
            $ZipPath
        )
    )

    Set-Content `
        -Path $HashPath `
        -Value $HashText `
        -Encoding ASCII

    Write-Host $HashText


    # -------------------------------------------------------------------------
    # Complete
    # -------------------------------------------------------------------------

    Write-Step "Windows release build complete"

    Write-Host "Application version:"
    Write-Host "  $Version"

    Write-Host ""
    Write-Host "Release version:"
    Write-Host "  $ReleaseVersion"

    Write-Host ""
    Write-Host "Windows version:"
    Write-Host "  $ExpectedWindowsVersion"

    Write-Host ""
    Write-Host "Git commit:"
    Write-Host "  $GitCommit"

    Write-Host ""
    Write-Host "Application:"
    Write-Host "  $ExecutablePath"

    Write-Host ""
    Write-Host "Release ZIP:"
    Write-Host "  $ZipPath"

    Write-Host ""
    Write-Host "SHA-256:"
    Write-Host "  $HashPath"

    Write-Host ""
    Write-Host (
        "Documents Organizer v$ReleaseVersion " +
        "Windows build completed successfully."
    )
}
finally {
    Pop-Location
}