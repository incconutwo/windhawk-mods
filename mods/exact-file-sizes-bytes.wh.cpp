// ==WindhawkMod==
// @id              exact-file-sizes-bytes
// @name            Exact File Sizes in Bytes
// @description     Displays file sizes in exact bytes without KB/MB units in Explorer. Acts as a companion to the 'Better file sizes' mod.
// @version         1.0
// @author          Companion Mod
// @include         explorer.exe
// @compilerOptions -lole32
// ==/WindhawkMod==

#include <windhawk_api.h>
#include <windows.h>
#include <propsys.h>
#include <combaseapi.h>

// Hardcoded PKEY_Size GUID to avoid any compiler linking issues
const PROPERTYKEY PKEY_Size_Local = { { 0xB725F130, 0x47EF, 0x101A, { 0xA5, 0xF1, 0x02, 0x60, 0x8C, 0x9E, 0xEB, 0xAC } }, 12 };

typedef HRESULT(WINAPI *PSFormatForDisplayAlloc_t)(REFPROPERTYKEY key, REFPROPVARIANT propvar, PROPDESC_FORMAT_FLAGS pdff, PWSTR* ppszDisplay);
PSFormatForDisplayAlloc_t PSFormatForDisplayAlloc_Original;

HRESULT WINAPI PSFormatForDisplayAlloc_Hook(REFPROPERTYKEY key, REFPROPVARIANT propvar, PROPDESC_FORMAT_FLAGS pdff, PWSTR* ppszDisplay) {
    // Intercept only the "Size" property column
    if (memcmp(&key.fmtid, &PKEY_Size_Local.fmtid, sizeof(GUID)) == 0 && key.pid == PKEY_Size_Local.pid) {
        ULONGLONG size = 0;
        bool hasSize = false;
        
        // Extract the raw file/folder size from the Property Variant
        if (propvar.vt == VT_UI8) {
            size = propvar.uhVal.QuadPart;
            hasSize = true;
        } else if (propvar.vt == VT_UI4) {
            size = propvar.ulVal;
            hasSize = true;
        }
        
        if (hasSize) {
            WCHAR buffer[64];
            wsprintfW(buffer, L"%I64u", size);
            
            // Format the raw number with thousands separators (e.g., 1,234,567)
            NUMBERFMTW fmt = {0};
            fmt.NumDigits = 0; // No decimals
            fmt.LeadingZero = 0;
            
            // Dynamically fetch the user's regional comma/period separators
            WCHAR groupSep[4] = L",";
            GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_STHOUSAND, groupSep, ARRAYSIZE(groupSep));
            fmt.lpThousandSep = groupSep;
            
            WCHAR decSep[4] = L".";
            GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_SDECIMAL, decSep, ARRAYSIZE(decSep));
            fmt.lpDecimalSep = decSep;
            
            WCHAR grouping[16] = L"3;0";
            GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_SGROUPING, grouping, ARRAYSIZE(grouping));
            fmt.Grouping = (grouping[0] >= L'0' && grouping[0] <= L'9') ? (grouping[0] - L'0') : 3;
            if (fmt.Grouping == 0) fmt.Grouping = 3;
            fmt.NegativeOrder = 1;
            
            WCHAR formatted[128];
            int ret = GetNumberFormatW(LOCALE_USER_DEFAULT, 0, buffer, &fmt, formatted, ARRAYSIZE(formatted));
            if (ret > 0) {
                // Return the custom string to Explorer
                *ppszDisplay = (PWSTR)CoTaskMemAlloc(ret * sizeof(WCHAR));
                if (*ppszDisplay) {
                    lstrcpyW(*ppszDisplay, formatted);
                    return S_OK; 
                }
            }
        }
    }
    
    // Fallback for everything else (Date, Name, Type, etc.)
    return PSFormatForDisplayAlloc_Original(key, propvar, pdff, ppszDisplay);
}

BOOL Wh_ModInit() {
    HMODULE propsys = LoadLibraryW(L"propsys.dll");
    if (propsys) {
        FARPROC proc = GetProcAddress(propsys, "PSFormatForDisplayAlloc");
        if (proc) {
            Wh_SetFunctionHook((void*)proc, (void*)PSFormatForDisplayAlloc_Hook, (void**)&PSFormatForDisplayAlloc_Original);
        }
    }
    return TRUE;
}