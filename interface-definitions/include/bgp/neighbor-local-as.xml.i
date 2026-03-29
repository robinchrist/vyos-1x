<!-- include start from bgp/neighbor-local-as.xml.i -->
<tagNode name="local-as">
  <properties>
    <help>Specify alternate ASN for this BGP process</help>
    <valueHelp>
      <format>u32:1-4294967294</format>
      <description>Autonomous System Number (asplain)</description>
    </valueHelp>
    <valueHelp>
      <format>&lt;0-65535&gt;.&lt;0-65535&gt;</format>
      <description>Autonomous System Number (asdot)</description>
    </valueHelp>
    <constraint>
      <validator name="bgp-as-number"/>
    </constraint>
  </properties>
  <children>
    <node name="no-prepend">
      <properties>
        <help>Disable prepending local-as from/to updates for eBGP peers</help>
      </properties>
      <children>
        <leafNode name="replace-as">
          <properties>
            <help>Prepend only local-as from/to updates for eBGP peers</help>
            <valueless/>
          </properties>
        </leafNode>
      </children>
    </node>
  </children>
</tagNode>
<!-- include end -->
