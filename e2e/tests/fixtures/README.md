# 公開 HEIC 測試素材

`IMG_2682.heic` 為未修改的 iPhone 7 HEIC 原檔，880,703 bytes，解碼尺寸 4032×3024。
其用途是讓本機與 CI 使用同一份實拍樣本；使用者的私人照片不放在此目錄。

- 來源：[Immich test-assets 原檔](https://github.com/immich-app/test-assets/blob/ec56cc6c1d76c45bc9615dc6ea232470a2b0a3a1/formats/heic/IMG_2682.heic)
- 固定 revision：`ec56cc6c1d76c45bc9615dc6ea232470a2b0a3a1`
- 授權：素材為 public domain，見同 revision 的 [README](https://github.com/immich-app/test-assets/blob/ec56cc6c1d76c45bc9615dc6ea232470a2b0a3a1/README.md)。儲存庫根目錄的 AGPL 授權與 README 對影像素材的 public domain 聲明分開適用。
- SHA-256：`2d9d8493696fc0054ecb4517699fec11e04bf507f1f529f6a4f293fcefdeb35e`

測試執行時不下載素材。原始 bytes 與 EXIF 均保留，以驗證原圖下載；請以公開樣本本身的內容與中繼資料作為測試資料，不改用私人照片。對應案例見 [`english-acceptance.spec.ts`](../english-acceptance.spec.ts)。
